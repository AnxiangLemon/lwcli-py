"""
按账号索引广播登录/扫码事件，供 WebSocket `/ws/account/{idx}` 订阅。
与机器人启动流程绑定：有 emit 时 LoginService 走流式扫码，无 emit 时走终端打印（兼容非 Web 场景）。
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, List

from aiohttp import web


class AccountEventHub:
    """同一账号可重放最近事件，避免「先启动后连 WS」错过 qr_ready。"""

    MAX_REPLAY = 48

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._subscribers: Dict[int, List[web.WebSocketResponse]] = {}
        self._replay: Dict[int, List[str]] = {}

    async def clear_replay(self, account_idx: int) -> None:
        async with self._lock:
            self._replay.pop(account_idx, None)

    async def register(self, account_idx: int, ws: web.WebSocketResponse) -> None:
        replay_snapshot: List[str] = []
        async with self._lock:
            self._subscribers.setdefault(account_idx, []).append(ws)
            replay_snapshot = list(self._replay.get(account_idx, []))
        for text in replay_snapshot:
            try:
                await ws.send_str(text)
            except Exception:
                break

    async def unregister(self, account_idx: int, ws: web.WebSocketResponse) -> None:
        async with self._lock:
            lst = self._subscribers.get(account_idx)
            if not lst:
                return
            if ws in lst:
                lst.remove(ws)
            if not lst:
                self._subscribers.pop(account_idx, None)

    async def emit(self, account_idx: int, msg: Dict[str, Any]) -> None:
        text = json.dumps(msg, ensure_ascii=False)
        async with self._lock:
            lst = self._replay.setdefault(account_idx, [])
            lst.append(text)
            while len(lst) > self.MAX_REPLAY:
                lst.pop(0)
            targets: List[web.WebSocketResponse] = list(
                self._subscribers.get(account_idx, [])
            )
        stale: List[web.WebSocketResponse] = []
        for w in targets:
            try:
                await w.send_str(text)
            except Exception:
                stale.append(w)
        for w in stale:
            await self.unregister(account_idx, w)

    def subscriber_count(self, account_idx: int) -> int:
        return len(self._subscribers.get(account_idx, []))
