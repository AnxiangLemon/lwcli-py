"""
插件能力示例（本文件以下划线开头，不会被 lwplugin_ 扫描加载）。

复制需要的片段到你的 lwplugin_xxx.py 即可。
"""

from __future__ import annotations

import asyncio

from lwapi import LwApiClient
from lwapi.models.msg import SyncMessageResponse
from src.plugins.bot_tasks import spawn_bot_task
from src.runtime.client_registry import get_client, iter_online_clients, require_client

# ---------------------------------------------------------------------------
# 1. 消息驱动（最常见）
# ---------------------------------------------------------------------------


async def handle(client: LwApiClient, resp: SyncMessageResponse) -> None:
  ...


# ---------------------------------------------------------------------------
# 2. 按 wxid 主动调用（任意时刻、任意协程内）
# ---------------------------------------------------------------------------


async def send_to_someone() -> None:
    client = await require_client("wxid_你的机器人")
    await client.msg.send_text_message(to_wxid="wxid_对方", content="你好")


async def broadcast_all_online() -> None:
    for wxid, client in (await iter_online_clients()).items():
        await client.msg.send_text_message(to_wxid="wxid_对方", content=f"来自 {wxid}")


# ---------------------------------------------------------------------------
# 3. 某账号上线后：启动协程做一次事（欢迎语、拉群数据等）
#    下线时框架会自动 cancel 由 spawn_bot_task 登记的任务
# ---------------------------------------------------------------------------

PLUGIN_ID = "your_plugin"


async def _welcome_once(client: LwApiClient) -> None:
    await asyncio.sleep(2)  # 等连接稳定
    await client.msg.send_text_message(
        to_wxid="filehelper",
        content=f"账号 {client.wxid} 已上线",
    )


async def on_bot_online(client: LwApiClient) -> None:
    wxid = (client.wxid or "").strip()
    spawn_bot_task(wxid, _welcome_once(client), name=f"{PLUGIN_ID}:welcome")


async def on_bot_offline(wxid: str) -> None:
    # 可选：释放该账号专属缓存；spawn 的任务已被框架 cancel
    ...


# ---------------------------------------------------------------------------
# 4. 进程启动后：某一时刻执行业务（不必等消息、不必等上线）
# ---------------------------------------------------------------------------


async def on_app_ready() -> None:
    async def _deferred() -> None:
        await asyncio.sleep(30)  # 启动 30 秒后
        online = await iter_online_clients()
        if not online:
            return
        # 对当时已在线的账号做一件事
        wxid, client = next(iter(online.items()))
        await client.msg.send_text_message(to_wxid="...", content="启动后提醒")

    asyncio.create_task(_deferred(), name=f"{PLUGIN_ID}:deferred")


# ---------------------------------------------------------------------------
# 5. 进程级长驻任务（轮询、定时巡检所有在线账号）
# ---------------------------------------------------------------------------


async def start_background() -> None:
    while True:
        await asyncio.sleep(300)
        for wxid, client in (await iter_online_clients()).items():
            c = await get_client(wxid)
            if c is None:
                continue
            # await c.msg.... 
            ...
