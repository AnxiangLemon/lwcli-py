from __future__ import annotations

from datetime import datetime

from loguru import logger

from lwapi import LwApiClient
from lwapi.models.msg import SyncMessageResponse

PLUGIN_ID = "demo_replies"
PLUGIN_TITLE = "演示：关键词自动回复"
PLUGIN_DESCRIPTION = "示例：你好/hi、菜单、pic 发图等，可在此文件基础上改业务逻辑。"


async def handle(client: LwApiClient, resp: SyncMessageResponse) -> None:
    wxid = client.wxid
    for msg in resp.addMsgs:
        if msg.msgType != 1:
            continue

        sender = msg.fromUserName.string
        content = msg.content.string.strip()
        time_str = datetime.fromtimestamp(msg.createTime).strftime("%m-%d %H:%M:%S")

        logger.info(f"[{PLUGIN_ID}] [{time_str}] {wxid} ← {sender}: {content}")

        if content in ["你好", "hi", "在吗", "在么"]:
            await client.msg.send_text_message(to_wxid=sender, content="我在的！自动回复～")

        elif "菜单" in content or "help" in content.lower():
            help_text = (
                "我是AI机器人，支持：\n1. 自动回复\n2. 拉群\n3. 发图片\n4. 改备注\n"
                "输入 功能+空格+参数 试试"
            )
            await client.msg.send_text_message(to_wxid=sender, content=help_text)
        elif "pic" in content:
            # 示例图链，生产环境请换成自己的地址或从配置读取
            image_url = (
                "http://103.40.14.118:12347/images/temp/"
                "53587046100@chatroom-wxid_fjnkvacehloh11-1764765791.png"
            )
            await client.msg.send_image_by_url(sender, image_url)
