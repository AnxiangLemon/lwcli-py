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
