from __future__ import annotations

from loguru import logger

from lwapi import LwApiClient
from lwapi.models.msg import SyncMessageResponse

from src.plugins.registry import resolve_handlers
from src.plugins.settings import load_enabled_ids


async def composite_message_handler(
    client: LwApiClient, resp: SyncMessageResponse
) -> None:
    """根据 config/plugins.json 的 enabled 顺序依次执行各插件。"""
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
