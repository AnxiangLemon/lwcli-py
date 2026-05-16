"""
在线 LwApiClient 注册表：BotService 在账号登录成功后注册，下线时注销。

插件与定时任务可通过本模块按 wxid 主动获取当前在线客户端，无需等待消息回调。
"""

from __future__ import annotations

import asyncio
from typing import Dict

from lwapi import LwApiClient


class ClientRegistry:
    """wxid -> 已登录且消息监听中的 LwApiClient（线程协程安全）。"""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._by_wxid: Dict[str, LwApiClient] = {}

    async def register(self, wxid: str, client: LwApiClient) -> None:
        key = (wxid or "").strip()
        if not key:
            return
        async with self._lock:
            self._by_wxid[key] = client

    async def unregister(self, wxid: str) -> None:
        key = (wxid or "").strip()
        if not key:
            return
        async with self._lock:
            self._by_wxid.pop(key, None)

    async def get(self, wxid: str) -> LwApiClient | None:
        key = (wxid or "").strip()
        if not key:
            return None
        async with self._lock:
            return self._by_wxid.get(key)

    async def list_wxids(self) -> list[str]:
        async with self._lock:
            return list(self._by_wxid.keys())

    async def snapshot(self) -> dict[str, LwApiClient]:
        """返回当前在线客户端的浅拷贝，便于遍历而不长期持锁。"""
        async with self._lock:
            return dict(self._by_wxid)

    def __len__(self) -> int:
        return len(self._by_wxid)


_registry = ClientRegistry()


async def register_online_client(wxid: str, client: LwApiClient) -> None:
    await _registry.register(wxid, client)


async def unregister_online_client(wxid: str) -> None:
    await _registry.unregister(wxid)


async def get_client(wxid: str) -> LwApiClient | None:
    """按 wxid 获取在线客户端；未启动或未登录完成时返回 None。"""
    return await _registry.get(wxid)


async def require_client(wxid: str) -> LwApiClient:
    """同 get_client，未在线时抛出 ValueError。"""
    client = await get_client(wxid)
    if client is None:
        raise ValueError(f"机器人未在线: {wxid!r}（请先在运维台启动并完成登录）")
    return client


async def list_online_wxids() -> list[str]:
    return await _registry.list_wxids()


async def iter_online_clients() -> dict[str, LwApiClient]:
    """遍历所有在线实例，例如定时群发、巡检。"""
    return await _registry.snapshot()


def online_count() -> int:
    """同步读取在线数量（仅用于日志/监控，精确查询请用 list_online_wxids）。"""
    return len(_registry)
