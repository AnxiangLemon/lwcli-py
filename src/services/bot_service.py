"""
多账号机器人运行时：每个账号一个 asyncio.Task，内部循环为「登录 → 收消息」。

职责概要：
- 使用 account_slot_key 作为任务字典键（备注+device_id），避免 device_id 重复时冲突；
- 调用 LoginService 完成登录，经 AccountEventHub 向 Web 推送扫码/错误；
- 登录成功后启动心跳、LoginClient 内在线维持任务（默认每 4h SecAutoAuth、每 24h Reportclientcheck）、
  以及登录后立即一次环境上报；消息处理委托给 message_handler.default_message_handler。
- 任务取消或 `LwApiClient` 退出时：`aclose` 会依次停止消息轮询并 `join_background_tasks`，
  使心跳与在线维持协程完全结束后再关闭连接。

注意：若构造本类时不传入 account_events，则二维码登录无法推送界面（emit 为空会失败），
正常 Web 入口应始终注入 EventHub。
"""

from __future__ import annotations

import asyncio
import os
from typing import Dict, Optional, Set

from dotenv import load_dotenv

from lwapi import LwApiClient
from lwapi.sync_utils import SyncMode, normalize_sync_mode

from src.account_loader import account_slot_key, save_accounts
from src.login_service import LoginService
from src.message_handler import default_message_handler
from src.runtime.account_events import AccountEventHub
from src.utils import log_account_ctx, setup_logger, effective_account_remark

load_dotenv()
BASE_URL = os.getenv("LWAPI_BASE_URL", "http://localhost:8081")
DEFAULT_MSG_SYNC_MODE: SyncMode = normalize_sync_mode(
    os.getenv("LWAPI_MSG_SYNC_MODE"),
    default="websocket",
)


def _env_int(name: str, default: int, minimum: int) -> int:
    try:
        v = int(os.getenv(name, str(default)))
    except ValueError:
        v = default
    return max(minimum, v)


class BotService:
    """管理多个账号机器人协程的启动、停止与运行槽位查询。"""

    def __init__(self, account_events: Optional[AccountEventHub] = None) -> None:
        self._tasks: Dict[str, asyncio.Task] = {}
        self._lock = asyncio.Lock()
        self._events = account_events
        self._login_pending: Set[int] = set()

    @property
    def login_pending_indices(self) -> Set[int]:
        """正在登录（含等扫码）的账号在 accounts.json 中的下标集合。"""
        return set(self._login_pending)

    async def start_one(
        self, account: dict, all_accounts: list, account_idx: int
    ) -> None:
        """若该槽位尚无活跃任务，则为该账号启动 _run_single_bot 协程。"""
        slot = account_slot_key(account)
        async with self._lock:
            if slot in self._tasks and not self._tasks[slot].done():
                return
            self._tasks[slot] = asyncio.create_task(
                self._run_single_bot(account, all_accounts, account_idx),
                name=f"bot-{slot[:80]}",
            )

    async def start_all(self, accounts: list) -> None:
        """顺序尝试启动列表中每个账号（已运行的槽位会被 start_one 跳过）。"""
        for i, account in enumerate(accounts):
            await self.start_one(account, accounts, i)

    def running_slot_keys(self) -> list[str]:
        """返回当前未结束的机器人任务对应的 account_slot_key 列表。"""
        return [k for k, v in self._tasks.items() if not v.done()]

    async def stop_for_account(self, account: dict) -> bool:
        """按账号行取消对应任务；若本来未运行则返回 False。"""
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
        """单账号主循环：异常后 sleep 再重连，直至任务被取消。"""
        remark = effective_account_remark(acc)
        ctx_token = log_account_ctx.set(remark)
        try:
            bot_logger = setup_logger(remark)
        except Exception:
            log_account_ctx.reset(ctx_token)
            raise

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
                        sec_iv = _env_int(
                            "LWAPI_SEC_AUTO_LOGIN_INTERVAL_SECONDS",
                            4 * 3600,
                            300,
                        )
                        report_iv = _env_int(
                            "LWAPI_REPORT_CLIENT_CHECK_INTERVAL_SECONDS",
                            24 * 3600,
                            3600,
                        )
                        client.login.start_keepalive(
                            sec_interval=sec_iv,
                            report_interval=report_iv,
                        )
                        if await client.login.report_client_check():
                            bot_logger.info(
                                f"【{remark}】客户端环境已上报（Reportclientcheck）"
                            )
                        else:
                            bot_logger.warning(
                                f"【{remark}】Reportclientcheck 未成功，将继续运行"
                            )
                        sync_mode = DEFAULT_MSG_SYNC_MODE
                        client.msg.start(
                            handler=default_message_handler,
                            mode=sync_mode,
                            wxid=wxid,
                        )
                        sync_label = (
                            "WebSocket"
                            if sync_mode == "websocket"
                            else "HTTP 长轮询"
                        )
                        bot_logger.success(
                            f"【{remark}】机器人已上线，wxid={wxid}，消息同步={sync_label}"
                        )
                        if self._events:
                            await emit(
                                {
                                    "event": "bot_online",
                                    "wxid": wxid,
                                    "sync_mode": sync_mode,
                                    "message": f"消息监听已启动（{sync_label}）",
                                }
                            )

                        hold = asyncio.get_running_loop().create_future()
                        await hold
                    except asyncio.CancelledError:
                        raise
                    except Exception as e:
                        bot_logger.exception(f"【{remark}】运行异常: {e}")
                        if self._events:
                            await emit(
                                {
                                    "event": "bot_error",
                                    "message": str(e),
                                }
                            )
                        await asyncio.sleep(10)
        finally:
            log_account_ctx.reset(ctx_token)
            self._login_pending.discard(account_idx)
