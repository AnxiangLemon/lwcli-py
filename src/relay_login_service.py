"""
本地（local）登录流程封装。

客户端按 lwapi 下发的 HttpSpec 用本机网络 POST 微信 MMTLS；
服务端负责组包、加解密与会话存储。与 LoginService（远程登录）并存。
"""

from __future__ import annotations

from typing import Awaitable, Callable, Optional, Tuple

from lwapi.exceptions import LoginError
from lwapi.models.relay import RelayProxyInfo

from .utils import logger as root_logger

EmitFn = Callable[[dict], Awaitable[None]]


class RelayLoginService:
    """组合 LwApiClient.relay 的 local 登录步骤。"""

    def __init__(self, client, device_id: str, proxy=None, remark: str = ""):
        self.client = client
        self.device_id = device_id
        self.proxy = self._to_relay_proxy(proxy)
        self.remark = remark

    @staticmethod
    def _to_relay_proxy(proxy) -> RelayProxyInfo:
        if not proxy or not isinstance(proxy, dict):
            return RelayProxyInfo()
        if any(k in proxy for k in ("proxyIp", "proxyUser", "proxyPassword")):
            return RelayProxyInfo(
                proxyIp=str(proxy.get("proxyIp") or ""),
                proxyUser=str(proxy.get("proxyUser") or ""),
                proxyPassword=str(proxy.get("proxyPassword") or ""),
            )
        host = str(proxy.get("host") or proxy.get("proxyIp") or "").strip()
        port = proxy.get("port")
        if host and port:
            return RelayProxyInfo(proxyIp=f"{host}:{port}")
        return RelayProxyInfo()

    async def login(
        self,
        saved_wxid: str = "",
        emit: Optional[EmitFn] = None,
    ) -> Tuple[str, str]:
        relay = self.client.relay

        if saved_wxid:
            self.client.set_wxid(saved_wxid)
            result = await relay.sec_auto_auth(
                self.device_id,
                saved_wxid,
                proxy=self.proxy,
            )
            if result and result.get("wxid"):
                wxid = str(result["wxid"])
                device_id = str(result.get("deviceId") or self.device_id)
                root_logger.success(f"【{self.remark}】local 二次登录成功 → {wxid}")
                if emit:
                    await emit(
                        {
                            "event": "sec_auto_ok",
                            "wxid": wxid,
                            "message": "已使用本地缓存登录，无需扫码",
                        }
                    )
                return wxid, device_id

        if not emit:
            raise LoginError(
                "需要 local 扫码登录但未提供事件推送（emit）。请从运维台启动本账号并保持 "
                "WebSocket 已连接，或在 config/accounts.json 中填入有效 wxid 后重试。"
            )

        root_logger.info(f"【{self.remark}】local 正在获取二维码...")
        wxid: Optional[str] = None
        device_out = self.device_id
        async for ev in relay.qr_login_poll(
            self.device_id,
            proxy=self.proxy,
        ):
            await emit(ev)
            if ev.get("event") == "success":
                wxid = ev.get("wxid")
                break
            if ev.get("event") == "qr_ready":
                device_out = ev.get("device_id") or device_out
            if ev.get("event") == "error":
                code = str(ev.get("code") or "")
                raise LoginError(
                    ev.get("message") or "local 二维码登录失败",
                    reason=code,
                )

        if not wxid:
            raise LoginError("local 登录未完成或已中断")

        self.client.set_wxid(wxid)
        root_logger.success(f"【{self.remark}】local 登录成功！wxid = {wxid}")
        return wxid, device_out
