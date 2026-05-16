"""
插件生命周期：机器人上下线通知、进程级后台任务。

可选钩子（在 lwplugin_*.py 中定义，非必须）：
- on_app_ready(): Web 进程启动后调用一次
- on_bot_online(client): 某账号登录并进入消息监听后调用（可 spawn_bot_task 发欢迎消息等）
- on_bot_offline(wxid): 该账号下线或任务结束时调用
- start_background(): 应用存活期间的长驻协程
"""

from __future__ import annotations

import asyncio
from typing import AsyncIterator, List

from aiohttp import web
from loguru import logger

from lwapi import LwApiClient

from src.plugins.bot_tasks import cancel_tasks_for_wxid
from src.plugins.registry import resolve_handlers
from src.plugins.settings import load_enabled_ids
from src.plugins.types import PluginSpec


def _enabled_specs() -> List[PluginSpec]:
    return resolve_handlers(load_enabled_ids())


async def notify_bot_online(client: LwApiClient) -> None:
    wxid = (client.wxid or "").strip()
    for spec in _enabled_specs():
        if spec.on_bot_online is None:
            continue
        try:
            await spec.on_bot_online(client)
        except Exception:
            logger.exception(f"插件 [{spec.id}] on_bot_online 异常 (wxid={wxid})")


async def notify_app_ready() -> None:
    for spec in _enabled_specs():
        if spec.on_app_ready is None:
            continue
        try:
            await spec.on_app_ready()
        except Exception:
            logger.exception(f"插件 [{spec.id}] on_app_ready 异常")


async def notify_bot_offline(wxid: str) -> None:
    key = (wxid or "").strip()
    await cancel_tasks_for_wxid(key)
    for spec in _enabled_specs():
        if spec.on_bot_offline is None:
            continue
        try:
            await spec.on_bot_offline(key)
        except Exception:
            logger.exception(f"插件 [{spec.id}] on_bot_offline 异常 (wxid={key})")


async def _run_background(spec: PluginSpec) -> None:
    assert spec.start_background is not None
    try:
        await spec.start_background()
    except asyncio.CancelledError:
        raise
    except Exception:
        logger.exception(f"插件 [{spec.id}] 后台任务异常退出")


async def plugin_background_lifespan(app: web.Application) -> AsyncIterator[None]:
    """aiohttp cleanup_ctx：on_app_ready → start_background，退出时统一 cancel。"""
    await notify_app_ready()
    tasks: list[asyncio.Task[None]] = []
    for spec in _enabled_specs():
        if spec.start_background is None:
            continue
        name = f"plugin-bg-{spec.id}"
        tasks.append(asyncio.create_task(_run_background(spec), name=name))
        logger.info(f"插件 [{spec.id}] 后台任务已启动")
    app["plugin_background_tasks"] = tasks
    yield
    for t in tasks:
        t.cancel()
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)
    logger.info("插件后台任务已全部停止")
