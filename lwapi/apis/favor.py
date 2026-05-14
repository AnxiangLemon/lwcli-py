# lwapi/apis/favor.py
"""微信收藏：参数由 SDK 组装，无需手写 JSON。"""

from __future__ import annotations

from typing import Any, Optional

from ..models.favor_requests import FavorDelParam, FavorGetFavItemParam, FavorSyncParam
from ..transport import AsyncHTTPTransport


class FavorClient:
    def __init__(self, transport: AsyncHTTPTransport) -> None:
        self._t = transport

    async def delete(self, fav_id: int, *, timeout: Optional[float] = None) -> Any:
        """删除指定收藏项。"""
        return await self._t.post(
            "/Favor/Del", json=FavorDelParam(fav_id=fav_id).to_api(), timeout=timeout
        )

    async def get_fav_info(self, *, timeout: Optional[float] = None) -> Any:
        """获取收藏列表或元数据。"""
        return await self._t.post("/Favor/GetFavInfo", json=None, timeout=timeout)

    async def get_fav_item(self, fav_id: int, *, timeout: Optional[float] = None) -> Any:
        """读取单条收藏详情。"""
        return await self._t.post(
            "/Favor/GetFavItem",
            json=FavorGetFavItemParam(fav_id=fav_id).to_api(),
            timeout=timeout,
        )

    async def sync(
        self, key_buf: Optional[str] = None, *, timeout: Optional[float] = None
    ) -> Any:
        """同步收藏（首次 key_buf 可空）。"""
        return await self._t.post(
            "/Favor/Sync", json=FavorSyncParam(key_buf=key_buf).to_api(), timeout=timeout
        )
