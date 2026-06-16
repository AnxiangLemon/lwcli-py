"""运维台进程内 Events WebSocket 后台生命周期。"""
from __future__ import annotations

from typing import AsyncIterator

from aiohttp import web
from loguru import logger

from lwapi.apis.events import EventsWsClient

from src.runtime.events_ws_holder import bind_events_ws_client, shutdown_events_ws


async def events_ws_background_lifespan(app: web.Application) -> AsyncIterator[None]:
    """注册 Events WS 客户端；实际连接在 JSON 账号 ImportUser 成功后再启动。"""
    client = EventsWsClient()
    bind_events_ws_client(client)
    app["events_ws_client"] = client
    yield
    await shutdown_events_ws()
    logger.info("Events WS 后台任务已停止")
