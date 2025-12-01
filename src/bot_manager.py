# src/bot_manager.py
import asyncio
from lwapi import LwApiClient
from loguru import logger
from .account_loader import load_accounts, save_accounts
from .login_service import LoginService
from .message_handler import default_message_handler
from .utils import setup_logger

ACTIVE_BOTS = {}
BOT_LOCK = asyncio.Lock()
BASE_URL = "http://localhost:8081"

async def start_all_bots():
    accounts = load_accounts()
    logger.info(f"准备启动 {len(accounts)} 个账号")

    tasks = []
    for acc in accounts:
        task = asyncio.create_task(run_single_bot(acc))
        tasks.append(task)

    await asyncio.gather(*tasks, return_exceptions=True)

async def run_single_bot(acc: dict):
    logger = setup_logger(acc.get("remark", acc["device_id"][:8]))
    device_id = acc["device_id"]
    remark = acc.get("remark", device_id[:8])
    saved_wxid = acc.get("wxid", "").strip()
    proxy = acc.get("proxy")

    while True:
        async with LwApiClient(BASE_URL) as client:
            try:
                login_service = LoginService(client, device_id, proxy, remark)
                wxid = await login_service.login(saved_wxid)

                # 登录成功 → 保存 wxid
                if not saved_wxid:
                    acc["wxid"] = wxid
                    save_accounts(load_accounts())

                # 启动心跳 + 消息监听
                client.login.start_heartbeat(interval=20)
                async with BOT_LOCK:
                    ACTIVE_BOTS[wxid] = client

                client.msg.start(handler=default_message_handler)
                logger.success(f"【{remark}】机器人已上线！")

                # 保持运行
                while True:
                    await asyncio.sleep(60)

            except Exception as e:
                logger.error(f"【{remark}】运行异常: {e}")
                await asyncio.sleep(10)