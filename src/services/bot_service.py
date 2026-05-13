from __future__ import annotations

import asyncio
import os
from typing import Dict, Optional, Set

from dotenv import load_dotenv
from loguru import logger

from lwapi import LwApiClient

from src.account_loader import save_accounts
from src.login_service import LoginService
from src.message_handler import default_message_handler
from src.runtime.account_events import AccountEventHub
from src.services.account_slot import account_slot_key
from src.utils import setup_logger

load_dotenv()
BASE_URL = os.getenv("LWAPI_BASE_URL", "http://localhost:8081")


class BotService:
    """机器人运行管理：启动流程与 bot.py 一致（缓存登录 → 否则扫码），Web 端通过 EventHub 推送扫码状态。"""

    def __init__(self, account_events: Optional[AccountEventHub] = None) -> None:
        self._tasks: Dict[str, asyncio.Task] = {}
        self._lock = asyncio.Lock()
        self._events = account_events
        self._login_pending: Set[int] = set()

    @property
    def login_pending_indices(self) -> Set[int]:
        return set(self._login_pending)

    async def start_one(
        self, account: dict, all_accounts: list, account_idx: int
    ) -> None:
        slot = account_slot_key(account)
        async with self._lock:
            if slot in self._tasks and not self._tasks[slot].done():
                return
            self._tasks[slot] = asyncio.create_task(
                self._run_single_bot(account, all_accounts, account_idx),
                name=f"bot-{slot[:80]}",
            )

    async def start_all(self, accounts: list) -> None:
        for i, account in enumerate(accounts):
            await self.start_one(account, accounts, i)

    def running_slot_keys(self) -> list[str]:
        return [k for k, v in self._tasks.items() if not v.done()]

    async def stop_for_account(self, account: dict) -> bool:
        slot = account_slot_key(account)
        async with self._lock:
            task = self._tasks.pop(slot, None)
        if task is None:
            return False
        if not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        return True

    async def _run_single_bot(
        self, acc: dict, all_accounts: list, account_idx: int
    ) -> None:
        remark = acc.get("remark", acc["device_id"][:8])
        bot_logger = setup_logger(remark)

        device_id = acc["device_id"]
        saved_wxid = acc.get("wxid", "").strip()
        proxy = acc.get("proxy")

        self._login_pending.add(account_idx)
        try:
            if self._events:
                await self._events.clear_replay(account_idx)

            async def emit(msg: dict) -> None:
                if self._events:
                    await self._events.emit(account_idx, msg)

            while True:
                wxid = ""
                async with LwApiClient(BASE_URL) as client:
                    try:
                        login_service = LoginService(
                            client, device_id, proxy, remark
                        )
                        use_emit = self._events is not None
                        wxid, real_device_id = await login_service.login(
                            saved_wxid,
                            emit=emit if use_emit else None,
                        )

                        saved_wxid = wxid
                        device_id = real_device_id
                        acc["device_id"] = real_device_id
                        acc["wxid"] = wxid
                        save_accounts(all_accounts)
                        self._login_pending.discard(account_idx)

                        if self._events:
                            await emit({"event": "login_saved", "wxid": wxid})

                        client.login.start_heartbeat(interval=20)
                        client.msg.start(handler=default_message_handler)
                        bot_logger.success(f"【{remark}】机器人已上线，wxid={wxid}")
                        if self._events:
                            await emit(
                                {
                                    "event": "bot_online",
                                    "wxid": wxid,
                                    "message": "消息监听已启动",
                                }
                            )

                        while True:
                            await asyncio.sleep(60)
                    except asyncio.CancelledError:
                        raise
                    except Exception as e:
                        logger.error(f"【{remark}】运行异常: {e}")
                        if self._events:
                            await emit(
                                {
                                    "event": "bot_error",
                                    "message": str(e),
                                }
                            )
                        await asyncio.sleep(10)
        finally:
            self._login_pending.discard(account_idx)

