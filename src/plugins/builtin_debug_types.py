"""
内置插件：调试输出非文本消息的 msgType（文本 msgType==1 跳过）。

启用后可在日志中看到图片/语音等类型摘要，便于对照协议字段。
"""

from __future__ import annotations

from loguru import logger

from lwapi import LwApiClient
from lwapi.models.msg import SyncMessageResponse

PLUGIN_ID = "debug_types"
PLUGIN_TITLE = "调试：非文本消息类型"
PLUGIN_DESCRIPTION = "在日志中打印图片/语音/视频等 msgType，便于排查（文本消息不打印）。"


async def handle(client: LwApiClient, resp: SyncMessageResponse) -> None:
    wxid = client.wxid
    for msg in resp.addMsgs:
        if msg.msgType == 1:
            continue
        labels = {
            3: "图片",
            34: "语音",
            43: "视频",
            49: "图文/小程序/分享",
            10000: "系统消息",
        }
        label = labels.get(msg.msgType, f"type={msg.msgType}")
        logger.debug(f"[{PLUGIN_ID}] wxid={wxid} ← {label}")
