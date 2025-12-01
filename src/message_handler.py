# src/message_handler.py
from lwapi.models.msg import SyncMessageResponse
from datetime import datetime

# 这就是以前写插件的地方 所有收到的消息都在这里处理

async def default_message_handler(client, resp: SyncMessageResponse):
    wxid = getattr(client.transport._config, "x_wxid", "")
    for msg in resp.addMsgs:
        print(f"这是原生的消息 { msg.msgType} 自行处理 {msg}")
        
        # 不是文本消息不处理
        # 1. 只处理文本消息（msgType == 1）
        if msg.msgType != 1:
            # 可选：打印其他类型看看
            if msg.msgType == 3:   print("  [图片消息]")
            if msg.msgType == 34:  print("  [语音消息]")
            if msg.msgType == 43:  print("  [视频消息]")
            if msg.msgType == 49:  print("  [图文/小程序/分享链接]")
            if msg.msgType == 10000: print("  [系统消息，如进群、退群、撤回]")
            continue
        
        sender = msg.fromUserName.string
        content = msg.content.string.strip()
        time_str = datetime.fromtimestamp(msg.createTime).strftime("%m-%d %H:%M:%S")

        print(f"[{time_str}] {wxid} ← {sender}: {content}")

        # ====================== 在这里写你的所有机器人逻辑 ======================
        if content in ["你好", "hi", "在吗", "在么"]:
            await client.msg.send_text_message(to_wxid=sender, content="我在的！自动回复～")

        elif "菜单" in content or "help" in content.lower():
            help_text = "我是AI机器人，支持：\n1. 自动回复\n2. 拉群\n3. 发图片\n4. 改备注\n输入 功能+空格+参数 试试"
            await client.msg.send_text_message(to_wxid=sender, content=help_text)

        # 继续加：发图文、卡片、撤回、好友管理、朋友圈、收藏……全都可以在这加
        # =========================================================================