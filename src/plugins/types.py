"""
消息插件描述结构：每个插件有稳定 id、展示用标题/说明，以及异步 handle 入口。

handle 签名与 LwApi MsgClient 回调一致：(LwApiClient, SyncMessageResponse) -> Awaitable[None]。

可选生命周期（在 lwplugin_*.py 中按需定义）：
- on_app_ready()：Web 进程启动后调用一次（可在此 asyncio.create_task / sleep 后执行业务）
- on_bot_online(client) / on_bot_offline(wxid)：单账号上下线
- start_background()：进程级长驻协程（应用存活期间一直运行）
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Awaitable, Callable, Optional

MessageHandler = Callable[..., Awaitable[None]]
AppReadyHandler = Callable[[], Awaitable[None]]
BotOnlineHandler = Callable[..., Awaitable[None]]
BotOfflineHandler = Callable[..., Awaitable[None]]
BackgroundStarter = Callable[[], Awaitable[None]]


@dataclass(frozen=True)
class PluginSpec:
    id: str
    title: str
    description: str
    handle: MessageHandler
    version: str = "1.0.0"
    author: str = ""
    on_app_ready: Optional[AppReadyHandler] = None
    on_bot_online: Optional[BotOnlineHandler] = None
    on_bot_offline: Optional[BotOfflineHandler] = None
    start_background: Optional[BackgroundStarter] = None
