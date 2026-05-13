"""
微信网页扫码二维码渲染。

说明：接口返回的 QrBase64 往往不是标准 PNG data URL，直接在浏览器里当图片用容易失败。
终端脚本 bot.py 使用的是「uuid → http://weixin.qq.com/x/{uuid} → qrcode 库生成图案」，
这里采用同一策略生成 PNG 再 base64，保证网页 <img> 能稳定显示。
"""

from __future__ import annotations

import base64
import io

import qrcode


def weixin_scan_url(uuid: str) -> str:
    """与 bot.generate_colored_qr 使用的数据一致：微信网页版扫码链接。"""
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
