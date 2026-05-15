"""
消息插件链的入口：按 config/plugins.json 中 enabled 顺序依次调用各插件的 handle。

LwApi 在收到一批同步消息后回调此处；每个插件应自行 try/except 或依赖本模块
统一捕获并打日志，避免单个插件异常中断后续插件。
"""

from __future__ import annotations

from loguru import logger

from lwapi import LwApiClient
from lwapi.models.msg import SyncMessageResponse

from src.message_inbox import append_sync_messages
from src.plugins.registry import resolve_handlers
from src.plugins.settings import load_enabled_ids


async def composite_message_handler(
    client: LwApiClient, resp: SyncMessageResponse
) -> None:
    """根据 config/plugins.json 的 enabled 顺序依次执行各插件。"""
    if resp.addMsgs:
        try:
            await append_sync_messages(client, resp)
        except Exception:
            logger.exception("消息入库（聚合用）失败")

    enabled = load_enabled_ids()
    specs = resolve_handlers(enabled)
    if not specs:
        logger.warning("未启用任何消息插件，请在运维台「插件管理」中勾选")
        return
    for spec in specs:
        try:
            await spec.handle(client, resp)
        except Exception:
            logger.exception(f"插件 [{spec.id}] 处理消息时异常")
