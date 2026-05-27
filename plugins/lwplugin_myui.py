"""
示例插件：带运维台弹窗设置页（panels/myui）。

私聊发送「myui」时按配置中的问候语回复；配置在设置页保存后立即生效，无需重启。
"""

from __future__ import annotations

from loguru import logger

from lwapi import LwApiClient
from lwapi.models.msg import SyncMessageResponse
from src.plugins.config import load_plugin_settings

PLUGIN_ID = "myui"
PLUGIN_TITLE = "示例：自定义设置页"
PLUGIN_DESCRIPTION = "演示插件自带 H5 设置面板；私聊「myui」可测试问候语配置。"
PLUGIN_VERSION = "1.0.0"
PLUGIN_AUTHOR = "LWAPI"
PLUGIN_ICON = "🎛️"

# 相对 plugins 目录；须含 index.html
PLUGIN_SETTINGS_PANEL = "panels/myui"

_DEFAULT_GREETING = "你好，这是 MyUI 插件！"


def _greeting() -> str:
    cfg = load_plugin_settings(PLUGIN_ID)
    text = (cfg.get("greeting") or "").strip()
    return text or _DEFAULT_GREETING


async def handle(client: LwApiClient, resp: SyncMessageResponse) -> None:
    wxid = (client.wxid or "").strip()
    for msg in resp.addMsgs or []:
        if msg.msgType != 1:
            continue
        sender = (msg.fromUserName.string or "").strip()
        if sender == wxid:
            continue
        content = (msg.content.string or "").strip()
        if content.lower() != "myui":
            continue
        reply = _greeting()
        await client.msg.send_text_message(to_wxid=sender, content=reply)
        logger.info(f"[{PLUGIN_ID}] 已回复 {sender}: {reply[:40]}")
