"""
微信登录流程封装（缓存二次登录 + 二维码登录）。

本仓库主入口为 Web 运维台：二维码阶段必须通过 emit 回调把 UUID、图片等
推送到前端 WebSocket；不再支持纯终端 ASCII 扫码。

若未传入 emit 且需要扫码，将抛出明确错误（请从网页启动并连接事件通道，
或预先在 accounts.json 中配置有效 wxid）。
"""

from __future__ import annotations

from typing import Awaitable, Callable, Optional, Tuple

from lwapi.exceptions import LoginError
from lwapi.models.login import ProxyInfo

from .services.qr_render import weixin_qr_png_base64, weixin_scan_url
from .utils import logger as root_logger

EmitFn = Callable[[dict], Awaitable[None]]


class LoginService:
    """组合 LwApiClient.login 的若干步骤，供 BotService 在单账号协程里调用。"""

    def __init__(self, client, device_id: str, proxy=None, remark: str = ""):
        self.client = client
        self.device_id = device_id
        self.proxy = ProxyInfo(**proxy) if proxy else None
        self.remark = remark

    async def login(
        self,
        saved_wxid: str = "",
        emit: Optional[EmitFn] = None,
    ) -> Tuple[str, str]:
        """
        先尝试缓存 wxid 二次登录；失败则拉二维码，经 emit 流式上报状态直至成功。

        emit 为 None 时：仅当二次登录已成功时才能继续；否则无法展示二维码。
        """
        login = self.client.login

        if saved_wxid:
            self.client.set_wxid(saved_wxid)
            if await login.sec_auto_login():
                root_logger.success(f"【{self.remark}】二次登录成功 → {saved_wxid}")
                if emit:
                    await emit(
                        {
                            "event": "sec_auto_ok",
                            "wxid": saved_wxid,
                            "message": "已使用本地缓存登录，无需扫码",
                        }
                    )
                return saved_wxid, self.device_id

        root_logger.info(f"【{self.remark}】正在获取二维码...")
        qr = await login.get_qr_code(self.device_id, self.proxy)

        if not emit:
            raise LoginError(
                "需要扫码登录但未提供事件推送（emit）。请从运维台启动本账号并保持 "
                "WebSocket 已连接，或在 config/accounts.json 中填入有效 wxid 后重试。"
            )

        scan_url = (qr.qr_url or "").strip() or weixin_scan_url(qr.uuid)
        png_b64 = weixin_qr_png_base64(qr.uuid)
        await emit(
            {
                "event": "qr_ready",
                "uuid": qr.uuid,
                "qr_base64": png_b64,
                "qr_url": scan_url,
                "device_id": qr.device_id,
            }
        )
        wxid: Optional[str] = None
        async for ev in login.stream_qr_status(
            qr.uuid,
            interval=3.0,
            timeout=300.0,
        ):
            await emit(ev)
            if ev.get("event") == "success":
                wxid = ev.get("wxid")
                break
            if ev.get("event") == "error":
                raise LoginError(
                    ev.get("message") or str(ev.get("code") or "二维码登录失败"),
                    reason=str(ev.get("code") or ""),
                )
        if not wxid:
            raise LoginError("登录未完成或已中断")

        self.client.set_wxid(wxid)
        root_logger.success(f"【{self.remark}】登录成功！wxid = {wxid}")
        return wxid, qr.device_id
