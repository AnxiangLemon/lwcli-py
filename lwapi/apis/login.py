# lwapi/apis/login.py
import asyncio
from enum import IntEnum
from typing import Optional, Dict, Any

import httpx
from httpx import ConnectError, NetworkError, TimeoutException
from loguru import logger

from ..transport import AsyncHTTPTransport
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
    EXPIRED = 3
    CANCELED = 4
    EXPIRED_OLD = -2007


class LoginClient:
    def __init__(self, transport: AsyncHTTPTransport):
        self.t = transport

        # 心跳任务控制（支持无限次启停）
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._stop_heartbeat = asyncio.Event()

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
        interval: int = 5,
        timeout: int = 300,  # 总超时秒数，比 max_retries 更直观
    ) -> str:
        deadline = asyncio.get_event_loop().time() + timeout
        last_status = None  # 记录上一次的状态，避免重复打印

        while True:
            if asyncio.get_event_loop().time() > deadline:
                raise asyncio.TimeoutError("二维码登录超时")

            try:
                data = await self.t.post(f"/Login/QRCheck?uuid={uuid}")
                # ====================== 统一提取 baseResponse ======================
                base_resp = data.get("baseResponse", {})
                ret = base_resp.get("ret") if isinstance(base_resp, dict) else None
                err_msg = (
                    base_resp.get("errMsg", {}).get("string")
                    if isinstance(base_resp.get("errMsg"), dict)
                    else base_resp.get("errMsg")
                )

                if ret == 0 and data.get("acctSectResp", {}).get("userName"):
                    wxid = data["acctSectResp"]["userName"]
                    nickname = data["acctSectResp"].get("nickName", "")
                    logger.success(f"登录成功！wxid={wxid} ({nickname})")
                    return wxid

                data = QRCheckResponse.model_validate(data)
                current_status = QRStatus(data.status)
                # 只有状态变化才打印（核心提示
                if current_status != last_status:
                    if current_status is QRStatus.NOT_SCANNED:
                        logger.info("等待微信扫码...（请打开微信扫一扫）")
                    elif current_status is QRStatus.SCANNED:
                        logger.info("已扫码！请在手机微信上点【登录】确认")
                    elif current_status in (QRStatus.EXPIRED, QRStatus.EXPIRED_OLD):
                        logger.error("二维码已过期")
                        raise LoginError("二维码已过期")
                    elif current_status is QRStatus.CANCELED:
                        logger.error("二维码已被取消")
                        raise LoginError("二维码已被取消")

                    last_status = current_status

                elif ret is not None and ret != 0:
                    logger.error("登录失败 ret=%s, msg=%s", ret, err_msg or "未知错误")
                    raise LoginError(f"登录失败: {err_msg or 'ret=' + str(ret)}")

            except LoginError:
                raise
            except (ConnectError, NetworkError, TimeoutException) as e:
                logger.warning(f"网络异常: {e}")
            except Exception as e:
                logger.error(f"检查二维码异常: {e}")

            await asyncio.sleep(
                min(interval, deadline - asyncio.get_event_loop().time())
            )

    # ==================== 永久心跳（支持重复登录） ====================
    async def _heartbeat_worker(self, interval: int = 60) -> None:
        self._stop_heartbeat.clear()

        try:
            while not self._stop_heartbeat.is_set():
                try:
                    await self.t.post("/Login/HeartBeat")
                
                except httpx.ReadTimeout:
                # 长轮询超时是正常现象，继续下一次
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

    # ==================== 其他登录相关接口 ====================
    async def logout(self) -> bool:
        self.stop_heartbeat()
        await self.t.post("/Login/LogOut")

    async def sec_auto_login(self) -> bool:
        try:
            data = await self.t.post("/Login/SecAutoAuth")
            logger.debug(data)  # 调试数据
            logger.success("二次免扫码登录成功")
            return True
        except LoginError as e:
            logger.error(f"二次登录失败: {e}")
            return False

    async def awaken(self) -> bool:
        try:
            await self.t.post("/Login/Awaken")
            logger.success("会话唤醒成功")
            return True
        except LoginError as e:
            logger.warning(f"会话唤醒失败: {e}")
            return False

    async def report_client_check(self) -> bool:
        try:
            await self.t.post("/Login/Reportclientcheck")
            logger.info("客户端环境上报成功")
            return True
        except LoginError as e:
            logger.error(f"环境上报失败: {e}")
            return False

    async def long_link_create(self) -> bool:
        try:
            await self.t.post("/Login/LongLinkCreate")
            logger.success("长连接创建成功")
            return True
        except LoginError as e:
            logger.error(f"长连接创建失败: {e}")
            return False

    async def long_link_remove(self) -> bool:
        self.stop_heartbeat()
        try:
            await self.t.post("/Login/LongRemove")
            logger.success("长连接已断开")
            return True
        except LoginError as e:
            logger.error(f"断开长连接失败: {e}")
            return False

    async def long_link_query(self) -> Dict[str, Any]:
        data = await self.t.post("/Login/LongQuery")
        logger.info("长连接状态查询成功")
        return data
