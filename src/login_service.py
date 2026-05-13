# src/login_service.py
from __future__ import annotations

from typing import Awaitable, Callable, Optional, Tuple

from lwapi.apis.login import LoginError
from lwapi.models.login import ProxyInfo

from .qr_printer import print_qr_terminal
from .services.qr_render import weixin_qr_png_base64, weixin_scan_url
from .utils import logger as root_logger

EmitFn = Callable[[dict], Awaitable[None]]


class LoginService:
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
        与 bot.py 一致：有 wxid 先二次登录；失败再走二维码。
        emit 不为空（Web）：只推网页事件，不在终端打印 ASCII 二维码；
        emit 为空（纯 CLI）：终端打印二维码并阻塞轮询。
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

        if emit:
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
                        ev.get("message") or ev.get("code") or "二维码登录失败"
                    )
            if not wxid:
                raise LoginError("登录未完成或已中断")
        else:
            url = f"http://weixin.qq.com/x/{qr.uuid}"
            print_qr_terminal(url)
            root_logger.info(f"【{self.remark}】设备id → {qr.device_id}")
            root_logger.info(f"【{self.remark}】请用微信扫码 → {qr.qr_url}")
            wxid = await login.check_qr_code(qr.uuid, timeout=300)

        self.client.set_wxid(wxid)
        root_logger.success(f"【{self.remark}】登录成功！wxid = {wxid}")
        return wxid, qr.device_id
