"""
账号级事件总线：把登录/扫码等 JSON 消息广播到已连接的 WebSocket。

每个账号在 accounts.json 中有固定下标 idx；BotService 在登录流程中 emit 到
本 Hub，运维台页面连接 /ws/account/{idx} 即可实时展示二维码与状态。

带短队列重放：避免用户「先点启动、后连 WS」时错过首条 qr_ready。
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, List

from aiohttp import web


class AccountEventHub:
    """维护 subscribers 与每账号最近若干条事件的环形缓冲，用于重放。"""

    MAX_REPLAY = 48

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._subscribers: Dict[int, List[web.WebSocketResponse]] = {}
        self._replay: Dict[int, List[str]] = {}

    async def clear_replay(self, account_idx: int) -> None:
        """某账号重新启动登录前清空旧重放缓存，避免错乱。"""
        async with self._lock:
            self._replay.pop(account_idx, None)

    async def register(self, account_idx: int, ws: web.WebSocketResponse) -> None:
        """新 WS 接入后立即发送该账号积压的重放消息。"""
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
        """写入重放队列并推送给当前该 idx 下所有活跃连接。"""
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
        """可选：用于观测某账号当前 WS 连接数。"""
        return len(self._subscribers.get(account_idx, []))
