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
BASE_URL2 = "http://103.91.208.68:8081"


async def start_all_bots():
    accounts = load_accounts()                      # ← 只读一次
    logger.info(f"准备启动 {len(accounts)} 个账号")

    tasks = []
    for acc in accounts:
        # 把整个 accounts 列表传进去！
        task = asyncio.create_task(run_single_bot(acc, accounts))
        tasks.append(task)

    await asyncio.gather(*tasks, return_exceptions=True)


# 增加一个参数：all_accounts
async def run_single_bot(acc: dict, all_accounts: list):
    remark = acc.get("remark", acc["device_id"][:8])
    logger = setup_logger(remark)

    device_id = acc["device_id"]
    saved_wxid = acc.get("wxid", "").strip()
    proxy = acc.get("proxy")

    while True:
        async with LwApiClient(BASE_URL2) as client:
            try:
                login_service = LoginService(client, device_id, proxy, remark)
                result = await login_service.login(saved_wxid)
                if isinstance(result, tuple):
                    wxid, real_device_id = result
                else:
                    wxid = result
                    real_device_id = device_id

                # 关键 3 行！扫码成功立刻永久保存
                acc["device_id"] = real_device_id
                acc["wxid"] = wxid
                save_accounts(all_accounts)
                
                client.login.start_heartbeat(interval=20)
                async with BOT_LOCK:
                    ACTIVE_BOTS[wxid] = client

                client.msg.start(handler=default_message_handler)
                logger.success(f"【{remark}】机器人已上线！")

                while True:
                    await asyncio.sleep(60)

            except Exception as e:
                logger.error(f"【{remark}】运行异常: {e}")
                await asyncio.sleep(10)