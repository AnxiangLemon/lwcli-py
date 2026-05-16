# lwapi/apis/login.py
import asyncio
import time
from enum import IntEnum
from typing import Optional, Dict, Any, Tuple, AsyncIterator, Callable, Awaitable

import httpx
from httpx import ConnectError, NetworkError, TimeoutException
from loguru import logger

from ..transport import AsyncHTTPTransport
from ..exceptions import ApiError, HttpError, LoginError, is_wrapped_request_timeout
from ..models.login import (
    QRGetRequest,
    QRGetResponse,
    QRCheckResponse,
    ProxyInfo,
)


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


def _qr_phase_for(status_val: Optional[int]) -> str:
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


def _parse_qr_status(payload: dict) -> Tuple[Optional[int], Optional[str], Optional[str], Optional[str], Optional[int], Optional[QRStatus]]:
    """从 QRCheck 响应解析 ret、wxid、verify_url、status。"""
    ret, err_msg = _extract_ret_errmsg(payload)
    wxid, _nickname = _extract_login_user(payload)
    verify_url: Optional[str] = None
    status_val: Optional[int] = None
    current_status: Optional[QRStatus] = None
    try:
        qr = QRCheckResponse.model_validate(payload)
        verify_url = getattr(qr, "verifyUrl", None) or payload.get("verifyUrl")
        status_val = getattr(qr, "status", None)
        if status_val is not None:
            try:
                current_status = QRStatus(status_val)
            except ValueError:
                current_status = None
    except Exception:
        verify_url = payload.get("verifyUrl")
    return ret, err_msg, wxid, verify_url, status_val, current_status


async def _iter_qr_poll(
    fetch_check: Callable[[], Awaitable[dict]],
    *,
    interval: float,
    timeout: float,
    stop_event: Optional[asyncio.Event] = None,
) -> AsyncIterator[Dict[str, Any]]:
    """
    二维码轮询核心循环。事件 type：
    poll | success | expired | canceled | api_error | verify_url | status |
    network_warning | poll_error | stopped | timeout
    """
    last_status: Optional[QRStatus] = None
    last_verify_url: Optional[str] = None
    net_failures = 0
    poll_seq = 0

    try:
        async with asyncio.timeout(timeout):
            while True:
                if stop_event is not None and stop_event.is_set():
                    yield {"type": "stopped", "message": "监听已取消"}
                    return
                try:
                    payload = await fetch_check()
                    net_failures = 0
                    poll_seq += 1
                    ret, err_msg, wxid, verify_url, status_val, current_status = (
                        _parse_qr_status(payload)
                    )

                    yield {
                        "type": "poll",
                        "seq": poll_seq,
                        "ret": ret,
                        "err_msg": err_msg,
                    }

                    if ret == 0 and wxid:
                        yield {
                            "type": "success",
                            "wxid": wxid,
                            "nickname": (_extract_login_user(payload)[1] or ""),
                        }
                        return

                    if ret == QRStatus.EXPIRED:
                        yield {"type": "expired", "message": "二维码已过期"}
                        return

                    if verify_url and verify_url != last_verify_url:
                        yield {"type": "verify_url", "url": verify_url}
                        last_verify_url = verify_url

                    if current_status is not None and current_status != last_status:
                        yield {
                            "type": "status",
                            "phase": _qr_phase_for(status_val),
                            "raw_status": status_val,
                            "ret": ret,
                            "status": current_status,
                        }
                        last_status = current_status

                    if current_status is QRStatus.CANCELED:
                        yield {"type": "canceled", "message": "二维码已被取消"}
                        return

                    if ret is not None and ret != 0:
                        yield {
                            "type": "api_error",
                            "message": err_msg or f"ret={ret}",
                            "ret": ret,
                        }
                        return

                except LoginError as e:
                    yield {"type": "login_error", "message": str(e)}
                    return
                except (ConnectError, NetworkError, TimeoutException) as e:
                    net_failures += 1
                    yield {
                        "type": "network_warning",
                        "message": str(e),
                        "failures": net_failures,
                    }
                except Exception as e:
                    net_failures += 1
                    yield {
                        "type": "poll_error",
                        "message": str(e),
                        "failures": net_failures,
                    }

                backoff = min(30.0, interval * (2 ** min(net_failures, 3)))
                await asyncio.sleep(max(0.2, backoff))

    except TimeoutError:
        yield {"type": "timeout", "message": "二维码登录超时"}


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
        轮询检测二维码状态（阻塞直到成功或失败）。
        与 stream_qr_status 共用 _iter_qr_poll 核心逻辑。
        """

        async def _fetch() -> dict:
            payload: dict = await self.t.post(f"/Login/QRCheck?uuid={uuid}")
            ret, err_msg = _extract_ret_errmsg(payload)
            logger.debug(
                f"QRCheck response: ret={ret}, errMsg={err_msg}, data={payload}"
            )
            return payload

        async for ev in _iter_qr_poll(
            _fetch, interval=interval, timeout=timeout
        ):
            t = ev["type"]
            if t == "poll":
                continue
            if t == "verify_url":
                logger.warning(
                    f"检测到安全验证链接，请手动访问完成验证：\n{ev['url']}"
                )
                continue
            if t == "status":
                st = ev.get("status")
                if st is QRStatus.NOT_SCANNED:
                    logger.info("等待微信扫码...（请打开微信扫一扫）")
                elif st is QRStatus.SCANNED:
                    logger.info("已扫码！请在手机微信上点【登录】确认")
                continue
            if t == "network_warning":
                logger.warning(
                    f"网络异常({ev.get('failures')})：{ev.get('message')}"
                )
                continue
            if t == "poll_error":
                logger.exception(
                    f"检查二维码异常({ev.get('failures')})：{ev.get('message')}"
                )
                continue
            if t == "success":
                wxid = ev["wxid"]
                nickname = ev.get("nickname") or ""
                logger.success(f"登录成功！wxid={wxid} ({nickname})")
                return wxid
            if t == "expired":
                logger.error("二维码已过期")
                raise LoginError(ev.get("message") or "二维码已过期")
            if t == "canceled":
                logger.error("二维码已被取消")
                raise LoginError(ev.get("message") or "二维码已被取消")
            if t == "api_error":
                msg = ev.get("message") or "未知错误"
                logger.error(f"登录失败: {msg}")
                raise LoginError(f"登录失败: {msg}")
            if t == "login_error":
                raise LoginError(ev.get("message") or "登录失败")
            if t == "timeout":
                raise asyncio.TimeoutError(
                    ev.get("message") or "二维码登录超时"
                )
            if t == "stopped":
                raise LoginError(ev.get("message") or "监听已取消")

        raise LoginError("二维码登录未完成")

    async def stream_qr_status(
        self,
        uuid: str,
        *,
        interval: float = 3.0,
        timeout: float = 300.0,
        stop_event: Optional[asyncio.Event] = None,
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        异步迭代 QRCheck 轮询结果，供 WebSocket 推送扫码状态。
        事件类型：poll | status | verify_url | success | error | stopped | warning
        """

        async def _fetch() -> dict:
            return await self.t.post(f"/Login/QRCheck?uuid={uuid}")

        async for ev in _iter_qr_poll(
            _fetch,
            interval=interval,
            timeout=timeout,
            stop_event=stop_event,
        ):
            t = ev["type"]
            if t == "poll":
                yield {
                    "event": "poll",
                    "seq": ev["seq"],
                    "ret": ev["ret"],
                    "err_msg": ev["err_msg"],
                }
            elif t == "success":
                yield {
                    "event": "success",
                    "wxid": ev["wxid"],
                    "nickname": ev.get("nickname") or "",
                }
            elif t == "expired":
                yield {
                    "event": "error",
                    "code": "expired",
                    "message": ev.get("message"),
                }
            elif t == "canceled":
                yield {
                    "event": "error",
                    "code": "canceled",
                    "message": ev.get("message"),
                }
            elif t == "api_error":
                yield {
                    "event": "error",
                    "code": "api",
                    "message": ev.get("message"),
                    "ret": ev.get("ret"),
                }
            elif t == "login_error":
                yield {
                    "event": "error",
                    "code": "login",
                    "message": ev.get("message"),
                }
            elif t == "timeout":
                yield {
                    "event": "error",
                    "code": "timeout",
                    "message": ev.get("message"),
                }
            elif t == "stopped":
                yield {"event": "stopped", "message": ev.get("message")}
            elif t == "verify_url":
                yield {"event": "verify_url", "url": ev["url"]}
            elif t == "status":
                yield {
                    "event": "status",
                    "phase": ev["phase"],
                    "raw_status": ev["raw_status"],
                    "ret": ev["ret"],
                }
            elif t == "network_warning":
                yield {
                    "event": "warning",
                    "code": "network",
                    "message": ev.get("message"),
                    "failures": ev.get("failures"),
                }
            elif t == "poll_error":
                yield {
                    "event": "warning",
                    "code": "poll_error",
                    "message": ev.get("message"),
                    "failures": ev.get("failures"),
                }

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
        sec_interval = max(3600, sec_interval)
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
            payload: dict = await self.t.post("/Login/SecAutoAuth")
            ret, err_msg = _extract_ret_errmsg(payload)
            if ret != 0:
                logger.debug(
                    f"二次免扫码登录未成功: ret={ret}, msg={err_msg or '未知错误'}"
                )
                return False

            logger.success("二次免扫码登录成功")
            return True
        except ApiError as e:
            # 缓存失效等为正常路径，随后会改走扫码
            if e.code == -1019 or "缓存" in (e.message or ""):
                logger.debug(f"二次登录缓存不可用: {e.message}")
            else:
                logger.warning(f"二次登录失败: {e}")
            return False
        except HttpError as e:
            logger.warning(f"二次登录网络异常: {e}")
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
