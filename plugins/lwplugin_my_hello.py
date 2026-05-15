"""
插件模板（以下划线开头，不会被加载）。

复制为 ``plugins/lwplugin_my_hello.py``，修改 ``PLUGIN_ID`` 后重启 ``python run.py``，
再在运维台「插件管理」或 ``config/plugins.json`` 中启用对应 id。

文件名必须以 ``lwplugin_`` 开头且位于 ``plugins/`` 首层才会被注册；
子目录可自由存放你的其它 Python 代码，不会被扫描。
"""

from __future__ import annotations

from loguru import logger

from lwapi import LwApiClient
from lwapi.models.msg import SyncMessageResponse

PLUGIN_ID = "my_hello"
PLUGIN_TITLE = "示例：你好世界"
PLUGIN_DESCRIPTION = "收到私聊文本「测试」时回复一句确认。"
PLUGIN_VERSION = "1.0.0"
PLUGIN_AUTHOR = "LWAPI"


async def handle(client: LwApiClient, resp: SyncMessageResponse) -> None:
    for msg in resp.addMsgs or []:
        if msg.msgType != 1:
            continue
        content = (msg.content.string or "").strip()
        sender = (msg.fromUserName.string or "").strip()
        if content == "测试":
            logger.info(f"[{PLUGIN_ID}] reply to {sender}")
            await client.msg.send_text_message(
                to_wxid=sender, content="插件已收到：测试"
            )
