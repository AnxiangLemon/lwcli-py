"""运维台进程内 Events WebSocket 后台生命周期。"""
from __future__ import annotations

from typing import AsyncIterator

from aiohttp import web
from loguru import logger

from lwapi.apis.events import EventsWsClient


async def events_ws_background_lifespan(app: web.Application) -> AsyncIterator[None]:
    """aiohttp cleanup_ctx：按 EVENT_WS / EVENT_KEY 可选启动 Events WS 客户端。"""
    client = EventsWsClient()
    await client.start()
    app["events_ws_client"] = client
    yield
    await client.stop()
    logger.info("Events WS 后台任务已停止")
