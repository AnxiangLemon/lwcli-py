"""Events WebSocket 配置与 URL 工具。"""
from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse


@dataclass(frozen=True)
class EventsConfig:
    ws_url: str
    event_key: str


_ENABLED_TRUTHY = frozenset({"1", "true", "yes", "on"})


def events_ws_enabled() -> bool:
    """是否开启 Events WS hook 消息接收（环境变量 EVENT_WS_ENABLED）。"""
    return (os.environ.get("EVENT_WS_ENABLED") or "").strip().lower() in _ENABLED_TRUTHY


def load_events_config() -> EventsConfig | None:
    """从环境变量读取 EVENT_WS / EVENT_KEY；未开启或任一缺失则返回 None。"""
    if not events_ws_enabled():
        return None
    ws_url = (os.environ.get("EVENT_WS") or "").strip()
    event_key = (os.environ.get("EVENT_KEY") or "").strip()
    if not ws_url or not event_key:
        return None
    return EventsConfig(ws_url=ws_url, event_key=event_key)


def build_events_ws_url(ws_url: str, event_key: str) -> str:
    """拼接管理端 Events WS 完整地址（附加 key 查询参数）。"""
    base = (ws_url or "").strip()
    key = (event_key or "").strip()
    if not base:
        raise ValueError("EVENT_WS 不能为空")
    if not key:
        raise ValueError("EVENT_KEY 不能为空")

    parsed = urlparse(base)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query["key"] = key
    return urlunparse(parsed._replace(query=urlencode(query)))
