"""管理端 Events WebSocket 客户端（hook 方式接收业务消息）。"""
from __future__ import annotations

import asyncio
import json
from typing import Awaitable, Callable, Optional

import aiohttp
from loguru import logger

from lwapi.events_parser import parse_ws_envelope
from lwapi.events_utils import EventsConfig, build_events_ws_url, events_ws_enabled, load_events_config
from lwapi.models.msg import AddMsg

EventHandler = Callable[[AddMsg, dict], Awaitable[None]]

_WS_HEARTBEAT_SEC = 30
_WS_SOCK_READ_TIMEOUT_SEC = 90


async def _default_event_handler(msg: AddMsg, envelope: dict) -> None:
    sender = (msg.fromUserName.string or "").strip()
    receiver = (msg.toUserName.string or "").strip()
    content = (msg.content.string or "").strip()
    logger.info(
        "Events WS 收到消息 "
        f"msgId={msg.msgId} from={sender} to={receiver} "
        f"msgType={msg.msgType} content={content!r}"
    )


class EventsWsClient:
    """
    连接管理端 ``/api/ws/events`` 接收 hook 推送的业务消息。

    与 ``MsgClient`` 的 ``/ws/sync`` 通道独立，不依赖登录或 ``LwApiClient``。
    """

    def __init__(self, *, ws_url: str = "", event_key: str = "") -> None:
        self._ws_url = (ws_url or "").strip()
        self._event_key = (event_key or "").strip()
        self._task: Optional[asyncio.Task[None]] = None
        self._stop_event = asyncio.Event()
        self._handler: Optional[EventHandler] = None
        self._ws_session: Optional[aiohttp.ClientSession] = None

    def _resolve_config(self) -> EventsConfig | None:
        if self._ws_url and self._event_key:
            return EventsConfig(ws_url=self._ws_url, event_key=self._event_key)
        return load_events_config()

    async def start(self, handler: EventHandler | None = None) -> None:
        """启动后台 WebSocket 监听；未开启或未配置 EVENT_WS/EVENT_KEY 时静默跳过。"""
        if self._task and not self._task.done():
            logger.warning("Events WS 已启动，请勿重复启动")
            return

        config = self._resolve_config()
        if config is None:
            if self._ws_url and self._event_key:
                logger.warning("Events WS 配置无效，跳过启动")
            elif not events_ws_enabled():
                logger.info("EVENT_WS_ENABLED 未开启，跳过 Events WS 启动")
            else:
                logger.info("未配置 EVENT_WS / EVENT_KEY，跳过 Events WS 启动")
            return

        self._handler = handler or _default_event_handler
        self._stop_event.clear()
        self._task = asyncio.create_task(self._ws_loop(config), name="events-ws")
        logger.success("Events WS 后台任务已启动")

    async def stop(self) -> None:
        """停止 WebSocket 监听并等待任务结束。"""
        self._stop_event.set()
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        if self._ws_session and not self._ws_session.closed:
            await self._ws_session.close()
            self._ws_session = None

    async def _dispatch(self, msg: AddMsg, envelope: dict) -> None:
        if not self._handler:
            return
        try:
            await self._handler(msg, envelope)
        except Exception:
            logger.exception("Events WS 消息处理函数异常")

    async def _ws_loop(self, config: EventsConfig) -> None:
        ws_url = build_events_ws_url(config.ws_url, config.event_key)
        logger.success(f"Events WebSocket 已启动: {config.ws_url}")

        reconnect_delay = 2.0
        while not self._stop_event.is_set():
            session: Optional[aiohttp.ClientSession] = None
            try:
                timeout = aiohttp.ClientTimeout(sock_read=_WS_SOCK_READ_TIMEOUT_SEC)
                session = aiohttp.ClientSession(timeout=timeout)
                self._ws_session = session
                async with session.ws_connect(
                    ws_url,
                    heartbeat=_WS_HEARTBEAT_SEC,
                    receive_timeout=None,
                ) as ws:
                    reconnect_delay = 2.0
                    logger.info("Events WebSocket 已连接")
                    while not self._stop_event.is_set():
                        try:
                            frame = await ws.receive()
                        except asyncio.TimeoutError:
                            logger.warning(
                                f"Events WebSocket 读超时（>{_WS_SOCK_READ_TIMEOUT_SEC}s 无数据），将重连"
                            )
                            break
                        except aiohttp.ClientError as e:
                            logger.warning(f"Events WebSocket 读取异常: {e}，将重连")
                            break

                        if frame.type == aiohttp.WSMsgType.TEXT:
                            parsed = parse_ws_envelope(frame.data)
                            if parsed:
                                _, add_msg = parsed
                                if isinstance(frame.data, dict):
                                    envelope = frame.data
                                else:
                                    try:
                                        envelope = json.loads(frame.data)
                                    except (json.JSONDecodeError, TypeError):
                                        envelope = {}
                                await self._dispatch(add_msg, envelope)
                        elif frame.type == aiohttp.WSMsgType.BINARY:
                            parsed = parse_ws_envelope(frame.data)
                            if parsed:
                                _, add_msg = parsed
                                await self._dispatch(add_msg, {})
                        elif frame.type in (
                            aiohttp.WSMsgType.CLOSE,
                            aiohttp.WSMsgType.CLOSED,
                            aiohttp.WSMsgType.ERROR,
                        ):
                            logger.warning("Events WebSocket 连接断开，将重连")
                            break
            except asyncio.CancelledError:
                break
            except Exception as e:
                if not self._stop_event.is_set():
                    logger.warning(f"Events WebSocket 连接异常: {e}，将重连")
            finally:
                if session is not None and not session.closed:
                    await session.close()
                if self._ws_session is session:
                    self._ws_session = None

            if self._stop_event.is_set():
                break
            logger.info(f"Events WebSocket 将在 {reconnect_delay:.0f}s 后重连")
            await asyncio.sleep(reconnect_delay)
            reconnect_delay = min(reconnect_delay * 1.5, 30.0)

        logger.info("Events WebSocket 已停止")
