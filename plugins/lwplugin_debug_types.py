"""
公共插件：调试输出

启用后可在日志中看到各类型消息摘要，便于对照协议字段编写业务插件。
"""

from __future__ import annotations

from loguru import logger

from lwapi import LwApiClient
from lwapi.models.msg import SyncMessageResponse

PLUGIN_ID = "debug_types"
PLUGIN_TITLE = "Demo-信息摘要"
PLUGIN_DESCRIPTION = "在日志中打印原始信息，便于根据字段编写插件"
PLUGIN_AUTHOR = "LWAPI"
PLUGIN_VERSION = "1.0.1"


async def handle(client: LwApiClient, resp: SyncMessageResponse) -> None:
    wxid = client.wxid
    for msg in resp.addMsgs or []:
        logger.debug(f"[{PLUGIN_ID}] wxid={wxid} ← {msg}")
