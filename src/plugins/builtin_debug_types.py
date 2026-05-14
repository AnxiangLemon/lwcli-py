"""
内置插件：调试输出

启用后可在日志中看到图片/语音等类型摘要，便于对照协议字段。
"""

from __future__ import annotations

from loguru import logger

from lwapi import LwApiClient
from lwapi.models.msg import SyncMessageResponse

PLUGIN_ID = "debug_types"
PLUGIN_TITLE = "调试消息"
PLUGIN_DESCRIPTION = "在日志中打印原始信息，便于根据字段编写插件"


async def handle(client: LwApiClient, resp: SyncMessageResponse) -> None:
    wxid = client.wxid
    for msg in resp.addMsgs:
        # if msg.msgType == 1:
        #     continue
        # labels = {
        #     3: "图片",
        #     34: "语音",
        #     43: "视频",
        #     49: "图文/小程序/分享",
        #     10000: "系统消息",
        # }
        # label = labels.get(msg.msgType, f"type={msg.msgType}")
        logger.debug(f"[{PLUGIN_ID}] wxid={wxid} ← {msg}")
