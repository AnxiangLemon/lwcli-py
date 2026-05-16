"""
示例插件：演示消息 / 上线协程 / 启动后调度 / 主动 require_client / 进程级后台。

在下方「配置区」填写 wxid；留空的项会自动跳过，不影响其它 demo 运行。
"""

from __future__ import annotations

import asyncio

from loguru import logger

from lwapi import LwApiClient
from lwapi.models.msg import SyncMessageResponse
from src.plugins.bot_tasks import spawn_bot_task
from src.runtime.client_registry import get_client, iter_online_clients, require_client

PLUGIN_ID = "my_demo"
PLUGIN_TITLE = "示例：全事件 Demo"
PLUGIN_DESCRIPTION = (
    "包括所有的事件类型示例：消息驱动、上线协程、启动后调度、主动 require_client、进程级后台；括所有的事件类型示例：消息驱动、上线协程、启动后调度、主动 require_client、进程级后台；括所有的事件类型示例：消息驱动、上线协程、启动后调度、主动 require_client、进程级后台；"
)
PLUGIN_VERSION = "1.0.0"
PLUGIN_AUTHOR = "LWAPI"
PLUGIN_ICON = "⚡"

# ---------------------------------------------------------------------------
# 配置区（按需填写，留空 "" 则跳过对应 demo）
# ---------------------------------------------------------------------------

# require_client / on_app_ready 主动发送时使用的机器人 wxid
BOT_WXID = ""

# 主动发送、上线欢迎等的目标 wxid（可填 filehelper）
TO_WXID = ""

# on_app_ready：进程启动后延迟多少秒再尝试主动发送
APP_READY_DELAY_SEC = 30

# on_bot_online：上线后延迟多少秒再发欢迎消息
ONLINE_WELCOME_DELAY_SEC = 2

# start_background：轮询间隔（秒）
BACKGROUND_INTERVAL_SEC = 300

# ---------------------------------------------------------------------------


def _filled(s: str) -> bool:
    return bool((s or "").strip())


async def handle(client: LwApiClient, resp: SyncMessageResponse) -> bool | None:
    """1. 消息驱动：打印收到的消息。"""
    for msg in resp.addMsgs or []:
        content = (msg.content.string or "").strip()
        sender = (msg.fromUserName.string or "").strip()
        wxid = client.wxid
        logger.info(f"[{PLUGIN_ID}] wxid={wxid} 收到消息 from={sender} content={content}")
    return None  # 不确定是否处理，继续让后续插件也有机会处理

async def _active_send_demo() -> None:
    """2. 按 wxid 主动发送（require_client）。"""
    if not _filled(BOT_WXID) or not _filled(TO_WXID):
        logger.debug(f"[{PLUGIN_ID}] 跳过主动发送：未配置 BOT_WXID / TO_WXID")
        return
    client = await require_client(BOT_WXID.strip())
    await client.msg.send_text_message(
        to_wxid=TO_WXID.strip(),
        content=f"[{PLUGIN_ID}] require_client 主动发送",
    )
    logger.info(f"[{PLUGIN_ID}] 主动发送完成 bot={BOT_WXID} to={TO_WXID}")


async def _welcome_once(client: LwApiClient) -> None:
    """3. 上线协程：延迟后发一条消息。"""
    await asyncio.sleep(max(0, ONLINE_WELCOME_DELAY_SEC))
    target = TO_WXID.strip() if _filled(TO_WXID) else "filehelper"
    await client.msg.send_text_message(
        to_wxid=target,
        content=f"[{PLUGIN_ID}] 账号已上线 wxid={client.wxid}",
    )
    logger.info(f"[{PLUGIN_ID}] 上线欢迎已发送 wxid={client.wxid} to={target}")


async def on_bot_online(client: LwApiClient) -> None:
    wxid = (client.wxid or "").strip()
    logger.info(f"[{PLUGIN_ID}] on_bot_online wxid={wxid}")
    spawn_bot_task(wxid, _welcome_once(client), name=f"{PLUGIN_ID}:welcome")


async def on_bot_offline(wxid: str) -> None:
    logger.info(f"[{PLUGIN_ID}] on_bot_offline wxid={wxid}")
    # spawn_bot_task 登记的任务已由框架 cancel；此处可做缓存清理等


async def on_app_ready() -> None:
    """4. 进程启动后：延迟执行（不依赖消息、不依赖刚上线）。"""

    async def _deferred() -> None:
        delay = max(0, APP_READY_DELAY_SEC)
        if delay:
            await asyncio.sleep(delay)
        if _filled(BOT_WXID) and _filled(TO_WXID):
            await _active_send_demo()
            return
        online = await iter_online_clients()
        if not online:
            logger.debug(f"[{PLUGIN_ID}] on_app_ready：暂无在线账号，跳过")
            return
        if _filled(TO_WXID):
            wxid, client = next(iter(online.items()))
            await client.msg.send_text_message(
                to_wxid=TO_WXID.strip(),
                content=f"[{PLUGIN_ID}] 启动后提醒（来自 {wxid}）",
            )
            logger.info(f"[{PLUGIN_ID}] on_app_ready 已用在线账号 {wxid} 发送")
        else:
            logger.debug(
                f"[{PLUGIN_ID}] on_app_ready：未配置 BOT_WXID/TO_WXID，"
                f"当前在线 {list(online.keys())}"
            )

    asyncio.create_task(_deferred(), name=f"{PLUGIN_ID}:app-ready")


async def start_background() -> None:
    """5. 进程级长驻：定期巡检所有在线账号。"""
    interval = max(60, BACKGROUND_INTERVAL_SEC)
    while True:
        await asyncio.sleep(interval)
        online = await iter_online_clients()
        if not online:
            logger.debug(f"[{PLUGIN_ID}] background tick：无在线账号")
            continue
        for wxid in online:
            client = await get_client(wxid)
            if client is None:
                continue
            logger.debug(f"[{PLUGIN_ID}] background tick wxid={wxid} ok")
            # 示例：取消注释并按需填写 TO_WXID
            # if _filled(TO_WXID):
            #     await client.msg.send_text_message(
            #         to_wxid=TO_WXID.strip(),
            #         content=f"[{PLUGIN_ID}] 定时巡检 from {wxid}",
            #     )
