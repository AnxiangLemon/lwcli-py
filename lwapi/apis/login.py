# lwapi/apis/login.py
import asyncio
import time
from enum import IntEnum
from typing import Optional, Dict, Any, Tuple, AsyncIterator

import httpx
from httpx import ConnectError, NetworkError, TimeoutException
from loguru import logger

from ..transport import AsyncHTTPTransport
from ..exceptions import ApiError, HttpError, is_wrapped_request_timeout
from ..models.login import (
    QRGetRequest,
    QRGetResponse,
    QRCheckResponse,
    ProxyInfo,
)


class LoginError(Exception):
    """登录模块专用业务异常"""

    pass


class QRStatus(IntEnum):
    NOT_SCANNED = 0
    SCANNED = 1
    CONFIRMING = 2  # 部分接口会返回此状态
    CANCELED = 4
    EXPIRED = -2007


def _extract_ret_errmsg(payload: dict) -> Tuple[Optional[int], Optional[str]]:
    """兼容 baseResponse 不存在 / errMsg 结构不一致的情况。"""
    base = payload.get("baseResponse")
    if not isinstance(base, dict):
        return None, None

    ret = base.get("ret")
    err = base.get("errMsg")

    # errMsg 可能是 {"string": "..."} 或直接是字符串
    if isinstance(err, dict):
        err = err.get("string")
    if err is not None:
        err = str(err)
    return ret, err


def _extract_login_user(payload: dict) -> Tuple[Optional[str], Optional[str]]:
    """登录成功时，从 acctSectResp 提取 wxid/nickname。"""
    acct = payload.get("acctSectResp")
    if not isinstance(acct, dict):
        return None, None
    wxid = acct.get("userName")
    nickname = acct.get("nickName") or ""
    return wxid, nickname


class LoginClient:
    def __init__(self, transport: AsyncHTTPTransport):
        self.t = transport

        # 心跳任务控制（支持无限次启停）
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._stop_heartbeat = asyncio.Event()

        # 缓存刷新：定时 SecAutoAuth、Reportclientcheck（与心跳同级的启停模型）
        self._maint_task: Optional[asyncio.Task] = None
        self._stop_maint = asyncio.Event()

    # ==================== 二维码登录 ====================
    async def get_qr_code(
        self,
        device_id: str,
        proxy: Optional[ProxyInfo] = None,
    ) -> QRGetResponse:
        """获取登录二维码"""
        payload = QRGetRequest(deviceId=device_id, proxy=proxy)
        data = await self.t.post("/Login/QRGet", json=payload.model_dump())
        return QRGetResponse.model_validate(data)

   
    async def check_qr_code(
        self,
        uuid: str,
        *,
        interval: float = 5,
        timeout: float = 300,
    ) -> str:
        """
        轮询检测二维码状态：
        - 状态变化才打提示
        - verifyUrl 只提示一次（即使状态不变也能提示）
        - 网络异常做轻量退避，避免刷屏+压接口
        """

        last_status: Optional["QRStatus"] = None
        last_verify_url: Optional[str] = None
        net_failures = 0  # 连续网络失败次数，用于退避

        try:
            async with asyncio.timeout(timeout):
                while True:
                    try:
                        payload: dict = await self.t.post(f"/Login/QRCheck?uuid={uuid}")
                        net_failures = 0  # 一旦成功请求就清零

                        ret, err_msg = _extract_ret_errmsg(payload)
                        logger.debug(f"QRCheck response: ret={ret}, errMsg={err_msg}, data={payload}")

                        # 1) 成功：ret=0 且有 userName
                        wxid, nickname = _extract_login_user(payload)
                        if ret == 0 and wxid:
                            logger.success(f"登录成功！wxid={wxid} ({nickname})")
                            return wxid

                        # 2) 过期：直接异常退出
                        if ret == QRStatus.EXPIRED:
                            logger.error("二维码已过期")
                            raise LoginError("二维码已过期")

                        # 3) 解析扫码状态（允许 extra，不影响 verifyUrl）
                        qr = QRCheckResponse.model_validate(payload)

                        # 4) verifyUrl：不依赖状态变化，只要出现/变化就提示一次
                        verify_url = getattr(qr, "verifyUrl", None) or payload.get("verifyUrl")
                        if verify_url and verify_url != last_verify_url:
                            logger.warning(f"检测到安全验证链接，请手动访问完成验证：\n{verify_url}")
                            last_verify_url = verify_url

                        # 5) 状态机提示：只在状态变化时输出
                        status_val = getattr(qr, "status", None)
                        current_status: Optional["QRStatus"] = None
                        if status_val is not None:
                            current_status = QRStatus(status_val)

                        if current_status is not None and current_status != last_status:
                            if current_status is QRStatus.NOT_SCANNED:
                                logger.info("等待微信扫码...（请打开微信扫一扫）")
                            elif current_status is QRStatus.SCANNED:
                                # 扫码了但未确认
                                logger.info("已扫码！请在手机微信上点【登录】确认")
                            elif current_status is QRStatus.CANCELED:
                                logger.error("二维码已被取消")
                                raise LoginError("二维码已被取消")
                            last_status = current_status

                        # 6) 其它 ret 错误：只有 ret 明确非 0 才算“失败”
                        if ret is not None and ret != 0:
                            logger.error(f"登录失败 ret={ret}, msg={err_msg or '未知错误'}")
                            raise LoginError(f"登录失败: {err_msg or 'ret=' + str(ret)}")

                    except LoginError:
                        raise
                    except (ConnectError, NetworkError, TimeoutException) as e:
                        # 网络异常：warning + 退避（避免刷屏）
                        net_failures += 1
                        logger.warning(f"网络异常({net_failures})：{e}")
                    except Exception as e:
                        # 其它异常：带堆栈，但不让它疯狂刷屏（同样用退避）
                        net_failures += 1
                        logger.exception(f"检查二维码异常({net_failures})：{e}")

                    # 退避睡眠：interval * 2^k，上限 30s（你可调）
                    backoff = min(30.0, interval * (2 ** min(net_failures, 3)))
                    await asyncio.sleep(max(0.2, backoff))

        except TimeoutError:
            # asyncio.timeout 抛的是 TimeoutError，这里换成你想要的信息
            raise asyncio.TimeoutError("二维码登录超时")

    async def stream_qr_status(
        self,
        uuid: str,
        *,
        interval: float = 3.0,
        timeout: float = 300.0,
        stop_event: Optional[asyncio.Event] = None,
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        异步迭代 QRCheck 轮询结果，供 WebSocket 推送扫码状态（替代阻塞版 check_qr_code）。
        事件类型：poll | status | verify_url | success | error | stopped
        """
        last_status: Optional[QRStatus] = None
        last_verify_url: Optional[str] = None
        net_failures = 0

        def phase_for(status_val: Optional[int]) -> str:
            if status_val is None:
                return "unknown"
            try:
                st = QRStatus(status_val)
            except ValueError:
                return "unknown"
            return {
                QRStatus.NOT_SCANNED: "waiting",
                QRStatus.SCANNED: "scanned",
                QRStatus.CONFIRMING: "confirming",
                QRStatus.CANCELED: "canceled",
            }.get(st, "unknown")

        try:
            async with asyncio.timeout(timeout):
                poll_seq = 0
                while True:
                    if stop_event is not None and stop_event.is_set():
                        yield {"event": "stopped", "message": "监听已取消"}
                        return
                    try:
                        payload: dict = await self.t.post(f"/Login/QRCheck?uuid={uuid}")
                        net_failures = 0
                        poll_seq += 1

                        ret, err_msg = _extract_ret_errmsg(payload)
                        wxid, nickname = _extract_login_user(payload)

                        yield {
                            "event": "poll",
                            "seq": poll_seq,
                            "ret": ret,
                            "err_msg": err_msg,
                        }

                        if ret == 0 and wxid:
                            yield {
                                "event": "success",
                                "wxid": wxid,
                                "nickname": nickname or "",
                            }
                            return

                        if ret == QRStatus.EXPIRED:
                            yield {
                                "event": "error",
                                "code": "expired",
                                "message": "二维码已过期",
                            }
                            return

                        qr = QRCheckResponse.model_validate(payload)
                        verify_url = getattr(qr, "verifyUrl", None) or payload.get(
                            "verifyUrl"
                        )
                        status_val = getattr(qr, "status", None)
                        current_status: Optional[QRStatus] = None
                        if status_val is not None:
                            try:
                                current_status = QRStatus(status_val)
                            except ValueError:
                                current_status = None

                        if verify_url and verify_url != last_verify_url:
                            yield {"event": "verify_url", "url": verify_url}
                            last_verify_url = verify_url

                        status_changed = current_status != last_status
                        if status_changed:
                            yield {
                                "event": "status",
                                "phase": phase_for(status_val),
                                "raw_status": status_val,
                                "ret": ret,
                            }
                            last_status = current_status

                        if current_status is QRStatus.CANCELED:
                            yield {
                                "event": "error",
                                "code": "canceled",
                                "message": "二维码已被取消",
                            }
                            return

                        if ret is not None and ret != 0:
                            yield {
                                "event": "error",
                                "code": "api",
                                "message": err_msg or f"ret={ret}",
                                "ret": ret,
                            }
                            return

                    except LoginError as e:
                        yield {"event": "error", "code": "login", "message": str(e)}
                        return
                    except (ConnectError, NetworkError, TimeoutException) as e:
                        net_failures += 1
                        yield {
                            "event": "warning",
                            "code": "network",
                            "message": str(e),
                            "failures": net_failures,
                        }
                    except Exception as e:
                        net_failures += 1
                        yield {
                            "event": "warning",
                            "code": "poll_error",
                            "message": str(e),
                            "failures": net_failures,
                        }

                    backoff = min(30.0, interval * (2 ** min(net_failures, 3)))
                    await asyncio.sleep(max(0.2, backoff))

        except TimeoutError:
            yield {"event": "error", "code": "timeout", "message": "二维码登录超时"}

    # ==================== 永久心跳（支持重复登录） ====================
    async def _heartbeat_worker(self, interval: int = 60) -> None:
        self._stop_heartbeat.clear()

        try:
            while not self._stop_heartbeat.is_set():
                try:
                    await self.t.post("/Login/HeartBeat", timeout=45.0)

                except httpx.ReadTimeout:
                    continue
                except HttpError as e:
                    if is_wrapped_request_timeout(e):
                        logger.debug("心跳请求超时，稍后重试")
                        await asyncio.sleep(2)
                        continue
                    logger.warning(f"心跳 HTTP 异常（将继续）: {e}")
                    await asyncio.sleep(5)
                    continue
                except LoginError as e:
                    logger.warning(f"心跳业务异常（将继续）: {e}")
                except (ConnectError, NetworkError, TimeoutException):
                    logger.warning("网络波动，5秒后重试")
                    await asyncio.sleep(5)
                    continue
                except asyncio.CancelledError:
                    logger.info("心跳任务被取消")
                    raise
                except ApiError as e:
                    # 到 lwapi 的 HTTP 已成功；微信侧超时/离线等由后端包装为 ApiError（常见 -2001），
                    # 与 httpx 直连异常不同，故单独按可恢复网络问题处理。
                    if e.code == -2001 or (
                        e.message
                        and (
                            "网络请求失败" in e.message
                            or "deadline exceeded" in e.message.lower()
                        )
                    ):
                        logger.warning(f"心跳：上游网络波动（将继续）: {e}")
                    else:
                        logger.warning(f"心跳 API 异常（将继续）: {e}")
                    await asyncio.sleep(5)
                    continue
                except Exception as e:
                    logger.exception(f"心跳未知异常: {e}")

                # 可取消的等待
                try:
                    await asyncio.wait_for(
                        self._stop_heartbeat.wait(), timeout=interval
                    )
                except asyncio.TimeoutError:
                    continue

        except asyncio.CancelledError:
            logger.info("心跳任务正常取消")
            raise
        finally:
            logger.info("心跳任务已彻底结束")

    def start_heartbeat(self, interval: int = 55) -> None:
        """登录成功后调用（可重复调用，自动清理旧任务）"""
        self.stop_heartbeat()  # 先确保干净

        self._heartbeat_task = asyncio.create_task(
            self._heartbeat_worker(interval), name="LoginClient-Heartbeat"
        )
        logger.success("心跳已启动")

    def stop_heartbeat(self) -> None:
        """立即停止心跳（安全、可重复调用）"""
        if self._stop_heartbeat.is_set():
            return

        self._stop_heartbeat.set()
        if self._heartbeat_task and not self._heartbeat_task.done():
            self._heartbeat_task.cancel()
            logger.info("正在停止心跳任务...")

    async def _maint_worker(self, sec_interval: int, report_interval: int) -> None:
        """按固定周期二次登录、环境上报；与 `_heartbeat_worker` 一样可被 cancel/stop。"""
        self._stop_maint.clear()
        next_sec = time.monotonic() + sec_interval
        next_report = time.monotonic() + report_interval
        try:
            while not self._stop_maint.is_set():
                now = time.monotonic()
                if now >= next_sec:
                    await self.sec_auto_login()
                    next_sec = time.monotonic() + sec_interval
                    continue
                if now >= next_report:
                    await self.report_client_check()
                    next_report = time.monotonic() + report_interval
                    continue
                deadline = min(next_sec, next_report)
                wait = deadline - now
                if wait <= 0:
                    continue
                try:
                    await asyncio.wait_for(
                        self._stop_maint.wait(), timeout=min(60.0, wait)
                    )
                    break
                except asyncio.TimeoutError:
                    continue
        except asyncio.CancelledError:
            logger.info("缓存刷新任务正常取消")
            raise
        finally:
            logger.info("缓存刷新任务已彻底结束")

    def start_keepalive(
        self,
        *,
        sec_interval: int = 4 * 3600,
        report_interval: int = 24 * 3600,
    ) -> None:
        """登录成功后启动：每隔 sec_interval 调用 SecAutoAuth，每隔 report_interval 调用 Reportclientcheck。"""
        self.stop_keepalive()
        sec_interval = 1800 #max(3600, sec_interval)
        report_interval = max(3600, report_interval)
        self._maint_task = asyncio.create_task(
            self._maint_worker(sec_interval, report_interval),
            name="LoginClient-KeepAlive",
        )
        logger.success(
            f"环境刷新（SecAutoAuth 每 {sec_interval}s，Reportclientcheck 每 {report_interval}s）"
        )

    def stop_keepalive(self) -> None:
        """立即停止缓存刷新任务（安全、可重复调用）。"""
        if self._stop_maint.is_set():
            return
        self._stop_maint.set()
        if self._maint_task and not self._maint_task.done():
            self._maint_task.cancel()
            logger.info("正在停止缓存刷新任务...")

    async def join_background_tasks(self) -> None:
        """
        停止并等待心跳、缓存刷新任务完全结束（关闭 transport 或账号退出前应调用）。
        """
        self.stop_heartbeat()
        self.stop_keepalive()
        for t in (self._heartbeat_task, self._maint_task):
            if t and not t.done():
                try:
                    await t
                except asyncio.CancelledError:
                    pass

    # ==================== 其他登录相关接口 ====================
    async def logout(self) -> bool:
        """退出登录并停止心跳、缓存刷新等后台任务。"""
        await self.join_background_tasks()
        await self.t.post("/Login/LogOut")
        return True

    async def sec_auto_login(self) -> bool:
        try:
            payload: dict =  await self.t.post("/Login/SecAutoAuth")
            ret, err_msg = _extract_ret_errmsg(payload)
           # logger.debug(f"SecAutoAuth response: ret={ret}, errMsg={err_msg}, data={payload}")
            if ret != 0:
                logger.error(f"二次免扫码登录失败: ret={ret}, msg={err_msg or '未知错误'}")
                return False
            
            
            logger.success("二次免扫码登录成功？")
            return True
        except (ApiError, HttpError) as e:
            logger.error(f"二次登录失败: {e}")
            return False

    async def awaken(self) -> bool:
        try:
            await self.t.post("/Login/Awaken")
            logger.success("会话唤醒成功")
            return True
        except (ApiError, HttpError) as e:
            logger.warning(f"会话唤醒失败: {e}")
            return False

    async def report_client_check(self) -> bool:
        try:
            await self.t.post("/Login/Reportclientcheck")
            logger.info("客户端环境上报成功")
            return True
        except (ApiError, HttpError) as e:
            logger.error(f"环境上报失败: {e}")
            return False
