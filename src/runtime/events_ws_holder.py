"""EVENT_WS 客户端持有者：JSON 账号上线后再按需连接，全部下线后断开。"""
from __future__ import annotations

import asyncio
from typing import Optional

from loguru import logger

from lwapi.apis.events import EventsWsClient
from lwapi.events_utils import events_ws_enabled

from src.events_message_bridge import events_plugin_handler

_client: Optional[EventsWsClient] = None
_subscribers = 0
_lock = asyncio.Lock()
_EVENTS_WS_CONNECT_TIMEOUT_SEC = 30.0


def bind_events_ws_client(client: EventsWsClient) -> None:
    """由 events_lifespan 在进程启动时注册客户端实例。"""
    global _client
    _client = client


def get_events_ws_client() -> EventsWsClient | None:
    return _client


async def subscribe_events_ws() -> None:
    """首个依赖 EVENT_WS 的 JSON 账号上线后启动 WebSocket 收消息。"""
    if not events_ws_enabled():
        return

    client = _client
    if client is None:
        logger.warning("EVENT_WS 已开启但未注册 EventsWsClient，跳过连接")
        return

    async with _lock:
        global _subscribers
        _subscribers += 1
        if _subscribers > 1:
            return

        await client.start(handler=events_plugin_handler)
        connected = await client.wait_connected(timeout=_EVENTS_WS_CONNECT_TIMEOUT_SEC)
        if not connected:
            logger.warning(
                "EVENT_WS 暂未连上服务端，后台将继续重连；"
                "请确认 LwApi 已启动且 EVENT_WS / EVENT_KEY 正确"
            )


async def unsubscribe_events_ws() -> None:
    """最后一个依赖 EVENT_WS 的 JSON 账号下线后断开 WebSocket。"""
    if not events_ws_enabled():
        return

    client = _client
    if client is None:
        return

    async with _lock:
        global _subscribers
        if _subscribers <= 0:
            return
        _subscribers -= 1
        if _subscribers > 0:
            return
        await client.stop()


async def shutdown_events_ws() -> None:
    """进程退出时强制停止（忽略引用计数）。"""
    global _subscribers
    _subscribers = 0
    client = _client
    if client is not None:
        await client.stop()
