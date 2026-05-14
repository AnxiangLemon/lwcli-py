# lwapi/apis/finder.py
"""视频号 Finder：参数由 SDK 组装。"""

from __future__ import annotations

from typing import Any, Optional

from ..transport import AsyncHTTPTransport


class FinderClient:
    def __init__(self, transport: AsyncHTTPTransport) -> None:
        self._t = transport

    async def user_prepare(self, wxid: str, *, timeout: Optional[float] = None) -> Any:
        """视频号用户准备（query 携带 wxid）。"""
        return await self._t.post(
            "/Finder/UserPrepare", json=None, params={"wxid": wxid}, timeout=timeout
        )
