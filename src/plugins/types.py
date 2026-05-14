"""
消息插件描述结构：每个插件有稳定 id、展示用标题/说明，以及异步 handle 入口。

handle 签名与 LwApi MsgClient 回调一致：(LwApiClient, SyncMessageResponse) -> Awaitable[None]。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Awaitable, Callable

MessageHandler = Callable[..., Awaitable[None]]


@dataclass(frozen=True)
class PluginSpec:
    id: str
    title: str
    description: str
    handle: MessageHandler
    version: str = "1.0.0"
    author: str = ""
