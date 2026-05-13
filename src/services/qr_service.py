from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv

from lwapi import LwApiClient
from lwapi.models.login import ProxyInfo

from .qr_render import weixin_qr_png_base64, weixin_scan_url

load_dotenv()
BASE_URL = os.getenv("LWAPI_BASE_URL", "http://localhost:8081")


@dataclass
class QrSession:
    uuid: str
    qr_url: str
    # qr_base64：本地生成的标准 PNG base64（与 bot.py 扫码内容一致），非接口原始 QrBase64
    qr_base64: str
    device_id: str


class QrService:
    """二维码登录服务：负责创建二维码与确认扫码登录。"""

    async def create_qr(self, account: dict) -> QrSession:
        proxy_data = account.get("proxy")
        proxy = ProxyInfo(**proxy_data) if proxy_data else None
        async with LwApiClient(BASE_URL) as client:
            qr = await client.login.get_qr_code(account["device_id"], proxy)
            # 接口里的 QrUrl / QrBase64 可能与浏览器 img 不兼容；展示图与 bot.py 一致用 uuid 本地绘制。
            scan_url = (qr.qr_url or "").strip() or weixin_scan_url(qr.uuid)
            png_b64 = weixin_qr_png_base64(qr.uuid)
            return QrSession(
                uuid=qr.uuid,
                qr_url=scan_url,
                qr_base64=png_b64,
                device_id=qr.device_id,
            )

    async def confirm_login(
        self,
        *,
        uuid: str,
        timeout: float = 180,
        saved_wxid: Optional[str] = None,
    ) -> str:
        async with LwApiClient(BASE_URL) as client:
            if saved_wxid:
                client.set_wxid(saved_wxid)
            wxid = await client.login.check_qr_code(uuid, timeout=timeout, interval=3)
            return wxid

