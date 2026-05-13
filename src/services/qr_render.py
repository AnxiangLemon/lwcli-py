"""
微信扫码用二维码的本地渲染（PNG → Base64）。

说明：LWAPI 返回的 QrBase64 往往不是标准 PNG，浏览器 <img> 直接展示易失败。
本模块用 uuid 拼出 weixin.qq.com 扫码链，再用 qrcode 库生成 PNG，与常见 bot 脚本一致。

被 LoginService（推送运维台图片）等调用。
"""

from __future__ import annotations

import base64
import io

import qrcode


def weixin_scan_url(uuid: str) -> str:
    """微信网页扫码链接（与 uuid 一一对应）。"""
    return f"http://weixin.qq.com/x/{uuid.strip()}"


def weixin_qr_png_base64(uuid: str) -> str:
    """生成 PNG 的纯 base64（不含 data:image 前缀），供前端 data URL 使用。"""
    url = weixin_scan_url(uuid)
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=8,
        border=2,
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")
