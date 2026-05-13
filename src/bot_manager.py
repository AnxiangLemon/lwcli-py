# src/bot_manager.py
import asyncio
from loguru import logger
from .account_loader import load_accounts
from .services.bot_service import BotService

_BOT_SERVICE = BotService()


async def start_all_bots():
    """兼容旧入口：启动配置中的全部机器人。"""
    accounts = load_accounts()
    logger.info(f"准备启动 {len(accounts)} 个账号")
    await _BOT_SERVICE.start_all(accounts)
    while True:
        await asyncio.sleep(60)


async def run_single_bot(acc: dict, all_accounts: list):
    """兼容旧调用：启动单个机器人。"""
    idx = next((i for i, a in enumerate(all_accounts) if a is acc), 0)
    await _BOT_SERVICE.start_one(acc, all_accounts, idx)
