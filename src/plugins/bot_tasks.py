"""
按 wxid 挂载的插件后台协程：在 on_bot_online 里 spawn，账号下线时由框架统一 cancel。

用法::

    from src.plugins.bot_tasks import spawn_bot_task

    async def on_bot_online(client: LwApiClient) -> None:
        wxid = (client.wxid or "").strip()
        spawn_bot_task(wxid, _send_welcome(client), name=f"{PLUGIN_ID}:welcome")
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Awaitable, Set

from loguru import logger

_tasks_by_wxid: dict[str, Set[asyncio.Task[None]]] = defaultdict(set)


def spawn_bot_task(
    wxid: str,
    coro: Awaitable[None],
    *,
    name: str = "",
) -> asyncio.Task[None]:
    """
    为指定 wxid 启动后台协程；该账号下线时 lifecycle 会 cancel 此处登记的全部任务。

    coro 应为协程对象（调用方写 ``_work(client)`` 而非 ``create_task``）。
    """
    key = (wxid or "").strip()
    if not key:
        raise ValueError("wxid 不能为空")

    async def _runner() -> None:
        try:
            await coro
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception(f"账号后台任务异常 wxid={key} name={name or '-'}")

    task_name = name or f"bot-task:{key}"
    task = asyncio.create_task(_runner(), name=task_name)
    _tasks_by_wxid[key].add(task)

    def _cleanup(t: asyncio.Task[None]) -> None:
        _tasks_by_wxid.get(key, set()).discard(t)

    task.add_done_callback(_cleanup)
    return task


async def cancel_tasks_for_wxid(wxid: str) -> None:
    """取消某 wxid 下所有由 spawn_bot_task 登记的任务。"""
    key = (wxid or "").strip()
    if not key:
        return
    tasks = list(_tasks_by_wxid.pop(key, set()))
    if not tasks:
        return
    for t in tasks:
        if not t.done():
            t.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
