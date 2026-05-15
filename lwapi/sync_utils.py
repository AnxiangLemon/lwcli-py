# lwapi/sync_utils.py
"""消息同步模式与 WebSocket URL 工具。"""
from __future__ import annotations

from typing import Literal
from urllib.parse import urlencode, urlparse

SyncMode = Literal["poll", "websocket"]

_POLL_ALIASES = frozenset({"poll", "polling", "http", "longpoll", "long_poll"})
_WS_ALIASES = frozenset({"websocket", "ws", "wss", "wssocket", "socket"})


def normalize_sync_mode(raw: str | None, *, default: SyncMode = "websocket") -> SyncMode:
    """将用户/配置中的同步方式归一化为 poll 或 websocket。"""
    if not raw or not str(raw).strip():
        return default
    key = str(raw).strip().lower()
    if key in _POLL_ALIASES:
        return "poll"
    if key in _WS_ALIASES:
        return "websocket"
    raise ValueError(f"未知消息同步方式: {raw!r}，可选 poll / websocket")


def build_msg_ws_url(base_url: str, wxid: str) -> str:
    """
    根据 HTTP base_url 与 wxid 构造消息同步 WebSocket 地址。

    示例：http://127.0.0.1:8081 + wxid_xxx
          -> ws://127.0.0.1:8081/ws/sync?wxid=wxid_xxx
    """
    wxid = (wxid or "").strip()
    if not wxid:
        raise ValueError("WebSocket 同步需要有效的 wxid")

    parsed = urlparse(base_url.strip())
    if not parsed.scheme:
        parsed = urlparse(f"http://{base_url.strip()}")

    scheme = "wss" if parsed.scheme == "https" else "ws"
    host = parsed.netloc or parsed.path
    if not host:
        raise ValueError(f"无法从 base_url 解析主机: {base_url!r}")

    query = urlencode({"wxid": wxid})
    return f"{scheme}://{host}/ws/sync?{query}"
