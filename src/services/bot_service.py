"""
多账号机器人运行时：每个账号一个 asyncio.Task，内部循环为「登录 → 收消息」。

职责概要：
- 使用 accounts.json 行下标作为任务字典键；登录后 device_id 可能回写，不宜再用备注+device_id 作键；
- 调用 LoginService 完成登录，经 AccountEventHub 向 Web 推送扫码/错误；
- 登录成功后启动 LoginClient 内在线维持任务（默认每 48h SecAutoAuth）；
  心跳与环境上报由服务端维护，客户端不再单独发送 HeartBeat / Reportclientcheck。
- 消息处理委托给 message_handler.default_message_handler。
- 任务取消或 `LwApiClient` 退出时：`aclose` 会依次停止消息轮询并 `join_background_tasks`，
  使在线维持协程完全结束后再关闭连接。

注意：若构造本类时不传入 account_events，则二维码登录无法推送界面（emit 为空会失败），
正常 Web 入口应始终注入 EventHub。
"""

from __future__ import annotations

import asyncio
import os
from typing import Dict, Optional, Set

from dotenv import load_dotenv

from src.app_paths import env_file, prepare_runtime

prepare_runtime()
load_dotenv(env_file())

from lwapi import LwApiClient
from lwapi.events_utils import events_ws_enabled
from lwapi.exceptions import ApiError, HttpError, LoginError
from lwapi.sync_utils import SyncMode, normalize_sync_mode

from src.account_loader import save_accounts
from src.login_service import (
    LoginService,
    apply_import_user_profile,
    build_import_user_payload,
    clear_session_import_fields,
    format_import_user_error,
    normalize_login_mode,
    parse_import_user_profile,
)
from src.relay_login_service import RelayLoginService
from src.message_handler import default_message_handler
from src.plugins.lifecycle import notify_bot_offline, notify_bot_online
from src.runtime.account_events import AccountEventHub
from src.runtime.client_registry import (
    get_client as registry_get_client,
    register_online_client,
    unregister_online_client,
)
from src.runtime.events_ws_holder import subscribe_events_ws, unsubscribe_events_ws
from src.utils import log_account_ctx, setup_logger, effective_account_remark

BASE_URL = os.getenv("LWAPI_BASE_URL", "http://localhost:8081")
DEFAULT_MSG_SYNC_MODE: SyncMode = normalize_sync_mode(
    os.getenv("LWAPI_MSG_SYNC_MODE"),
    default="websocket",
)


def _merge_account_profile(
    acc: dict,
    *,
    nickname: str = "",
    avatar_url: str = "",
) -> bool:
    """将扫码/登录得到的昵称与头像写入账号配置，有变化时返回 True。"""
    changed = False
    nick = (nickname or "").strip()
    avatar = (avatar_url or "").strip()
    if nick and acc.get("nickname") != nick:
        acc["nickname"] = nick
        changed = True
    if avatar and acc.get("avatar_url") != avatar:
        acc["avatar_url"] = avatar
        changed = True
    return changed


class JsonImportError(Exception):
    """JSON 账号 ImportUser 或上线等待失败。"""

    def __init__(
        self,
        message: str,
        *,
        code: int | str = "",
        session_cleared: bool = False,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.session_cleared = session_cleared


def _env_int(name: str, default: int, minimum: int) -> int:
    try:
        v = int(os.getenv(name, str(default)))
    except ValueError:
        v = default
    return max(minimum, v)


class BotService:
    """管理多个账号机器人协程的启动、停止与运行槽位查询。"""

    def __init__(self, account_events: Optional[AccountEventHub] = None) -> None:
        self._tasks: Dict[int, asyncio.Task] = {}
        self._json_ready_futures: Dict[int, asyncio.Future] = {}
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
        """若该账号行尚无活跃任务，则为该账号启动 _run_single_bot 协程。"""
        async with self._lock:
            task = self._tasks.get(account_idx)
            if task is not None and not task.done():
                return
            remark = effective_account_remark(account)
            self._tasks[account_idx] = asyncio.create_task(
                self._run_single_bot(account, all_accounts, account_idx),
                name=f"bot-{account_idx}-{remark[:40]}",
            )

    async def start_json_one(
        self,
        account: dict,
        all_accounts: list,
        account_idx: int,
        *,
        wait_ready: bool = True,
        timeout: float = 90.0,
    ) -> dict:
        """
        启动 JSON 导入账号常驻任务：ImportUser → 注册 client → 保活。

        wait_ready 为 True 时阻塞至 ImportUser 成功并返回资料摘要；失败抛出 JsonImportError。
        """
        if normalize_login_mode(account.get("login_mode", "local")) != "json":
            raise ValueError("仅 JSON 导入账号可调用 start_json_one")

        remark = effective_account_remark(account)
        ready_fut: Optional[asyncio.Future] = None

        async with self._lock:
            task = self._tasks.get(account_idx)
            if task is not None and not task.done():
                await self._cancel_task_unlocked(account_idx, task)

            if wait_ready:
                ready_fut = asyncio.get_running_loop().create_future()
                self._json_ready_futures[account_idx] = ready_fut

            self._tasks[account_idx] = asyncio.create_task(
                self._run_json_bot(account, all_accounts, account_idx),
                name=f"json-bot-{account_idx}-{remark[:40]}",
            )

        if not wait_ready or ready_fut is None:
            return {}

        try:
            return await asyncio.wait_for(ready_fut, timeout=timeout)
        except asyncio.TimeoutError:
            await self.stop_for_account(account_idx, remark=remark)
            raise JsonImportError("ImportUser 超时", code="timeout") from None
        except asyncio.CancelledError:
            raise JsonImportError("ImportUser 已取消", code="canceled") from None

    async def _cancel_task_unlocked(
        self, account_idx: int, task: asyncio.Task
    ) -> None:
        """在已持有 _lock 时取消任务并等待结束。"""
        self._tasks.pop(account_idx, None)
        ready = self._json_ready_futures.pop(account_idx, None)
        if ready is not None and not ready.done():
            ready.cancel()
        if not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    async def start_all(self, accounts: list) -> None:
        """顺序尝试启动列表中每个账号（已运行的槽位会被 start_one 跳过）。"""
        for i, account in enumerate(accounts):
            await self.start_one(account, accounts, i)

    def running_account_indices(self) -> set[int]:
        """返回当前未结束的机器人任务对应的 accounts.json 行下标集合。"""
        return {i for i, t in self._tasks.items() if not t.done()}

    async def stop_for_account(self, account_idx: int, *, remark: str = "") -> bool:
        """按账号行下标取消对应任务；若本来未运行则返回 False。"""
        async with self._lock:
            task = self._tasks.pop(account_idx, None)
        if task is None:
            self._login_pending.discard(account_idx)
            if remark:
                setup_logger(remark).info(f"【{remark}】停止请求：账号未在运行")
            return False
        if not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        return True

    async def send_text_message(self, bot_wxid: str, to_wxid: str, content: str) -> dict:
        """
        使用当前在线的机器人客户端发送文本（需该账号机器人已启动且已登录）。

        Returns:
            LwApi 原始返回 dict（含 code / message / data）。
        """
        b = (bot_wxid or "").strip()
        t = (to_wxid or "").strip()
        c = (content or "").strip()
        if not b or not t or not c:
            raise ValueError("bot_wxid、to_wxid、content 均不能为空")
        client = await registry_get_client(b)
        if client is None:
            raise ValueError("该机器人未在线：请先在账号列表启动对应机器人并完成登录")
        return await client.msg.send_text_message(t, c)

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
        login_mode = normalize_login_mode(acc.get("login_mode", "local"))

        self._login_pending.add(account_idx)
        try:
            if self._events:
                await self._events.clear_replay(account_idx)

            async def emit(msg: dict) -> None:
                ev = msg.get("event")
                if ev == "status":
                    if _merge_account_profile(
                        acc,
                        nickname=str(
                            msg.get("nick_name") or msg.get("nickname") or ""
                        ),
                        avatar_url=str(
                            msg.get("head_img_url") or msg.get("avatar") or ""
                        ),
                    ):
                        save_accounts(all_accounts)
                elif ev == "success":
                    if _merge_account_profile(
                        acc,
                        nickname=str(msg.get("nickname") or ""),
                        avatar_url=str(
                            msg.get("head_img_url")
                            or msg.get("avatar")
                            or msg.get("avatar_url")
                            or ""
                        ),
                    ):
                        save_accounts(all_accounts)
                if self._events:
                    await self._events.emit(account_idx, msg)

            while True:
                wxid = ""
                async with LwApiClient(BASE_URL) as client:
                    try:
                        if login_mode == "local":
                            login_service = RelayLoginService(
                                client, device_id, proxy, remark
                            )
                        else:
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
                            await emit(
                                {
                                    "event": "login_saved",
                                    "wxid": wxid,
                                    "nickname": acc.get("nickname") or "",
                                    "avatar_url": acc.get("avatar_url") or "",
                                }
                            )

                        # 服务端维护心跳、在线状态与环境上报，客户端只需保持连接并周期性 SecAutoAuth
                        # （默认 48h）。
                        sec_iv = _env_int(
                            "LWAPI_SEC_AUTO_LOGIN_INTERVAL_SECONDS",
                            48 * 3600,
                            3600,
                        )
                        client.login.start_keepalive(sec_interval=sec_iv)
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

                        await register_online_client(wxid, client)
                        await notify_bot_online(client)
                        try:
                            hold = asyncio.get_running_loop().create_future()
                            await hold
                        finally:
                            await notify_bot_offline(wxid)
                            await unregister_online_client(wxid)
                    except asyncio.CancelledError:
                        bot_logger.info(f"【{remark}】账号已停止")
                        raise
                    except LoginError as e:
                        if e.reason == "canceled":
                            bot_logger.info(
                                f"【{remark}】扫码已取消，已停止登录"
                            )
                            if self._events:
                                await emit(
                                    {
                                        "event": "login_interrupted",
                                        "code": "canceled",
                                        "message": e.message or "二维码已被取消",
                                    }
                                )
                            break
                        if e.recoverable:
                            bot_logger.info(
                                f"【{remark}】登录中断（{e.reason or 'unknown'}）: {e.message}"
                            )
                            if self._events:
                                await emit(
                                    {
                                        "event": "login_interrupted",
                                        "code": e.reason,
                                        "message": e.message,
                                    }
                                )
                            await asyncio.sleep(2)
                        else:
                            bot_logger.warning(
                                f"【{remark}】登录失败: {e.message}"
                            )
                            if self._events:
                                await emit(
                                    {
                                        "event": "bot_error",
                                        "message": e.message,
                                    }
                                )
                            await asyncio.sleep(10)
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

    def _resolve_json_ready_future(
        self, account_idx: int, result: dict | BaseException
    ) -> None:
        ready = self._json_ready_futures.pop(account_idx, None)
        if ready is None or ready.done():
            return
        if isinstance(result, BaseException):
            ready.set_exception(result)
        else:
            ready.set_result(result)

    async def _run_json_bot(
        self, acc: dict, all_accounts: list, account_idx: int
    ) -> None:
        """JSON 导入账号：ImportUser 后注册在线客户端，收消息走 EVENT_WS（若已开启）。

        会话与环境由 LwApi 服务端在 ImportUser 后维护，不启动 SecAutoAuth 环境刷新。
        """
        remark = effective_account_remark(acc)
        ctx_token = log_account_ctx.set(remark)
        bot_logger = setup_logger(remark)
        wxid = ""

        try:
            try:
                payload = build_import_user_payload(acc)
            except ValueError as e:
                self._resolve_json_ready_future(account_idx, JsonImportError(str(e)))
                bot_logger.warning(f"【{remark}】JSON 会话字段不完整: {e}")
                return

            wxid = str(payload.get("wxid") or acc.get("wxid") or "").strip()
            use_events_ws = False

            async with LwApiClient(BASE_URL) as client:
                try:
                    try:
                        data = await client.login.import_user(payload)
                    except ApiError as e:
                        err_msg = format_import_user_error(
                            e.message or "ImportUser 失败"
                        )
                        session_cleared = clear_session_import_fields(acc)
                        acc.pop("import_connected", None)
                        save_accounts(all_accounts)
                        self._resolve_json_ready_future(
                            account_idx,
                            JsonImportError(
                                err_msg,
                                code=e.code,
                                session_cleared=session_cleared,
                            ),
                        )
                        bot_logger.warning(
                            f"【{remark}】ImportUser 失败: {e.message}"
                        )
                        return
                    except HttpError as e:
                        err_msg = format_import_user_error(
                            e.message or "请求 LwApi 失败"
                        )
                        self._resolve_json_ready_future(
                            account_idx,
                            JsonImportError(err_msg, code=e.status_code),
                        )
                        bot_logger.warning(
                            f"【{remark}】ImportUser 请求失败: {e.message}"
                        )
                        return

                    profile_updated = apply_import_user_profile(acc, data)
                    acc["import_connected"] = True
                    save_accounts(all_accounts)
                    nickname, avatar_url = parse_import_user_profile(data)
                    self._resolve_json_ready_future(
                        account_idx,
                        {
                            "data": data,
                            "nickname": acc.get("nickname") or nickname,
                            "avatar_url": acc.get("avatar_url") or avatar_url,
                            "profile_updated": profile_updated,
                        },
                    )

                    client.set_wxid(wxid)

                    if not events_ws_enabled():
                        sync_mode = DEFAULT_MSG_SYNC_MODE
                        client.msg.start(
                            handler=default_message_handler,
                            mode=sync_mode,
                            wxid=wxid,
                        )
                        recv_label = (
                            "WebSocket"
                            if sync_mode == "websocket"
                            else "HTTP 长轮询"
                        )
                    else:
                        recv_label = "EVENT_WS"

                    await register_online_client(wxid, client)
                    await notify_bot_online(client)
                    if events_ws_enabled():
                        await subscribe_events_ws()
                        use_events_ws = True

                    bot_logger.success(
                        f"【{remark}】JSON 账号已上线，wxid={wxid}，收消息={recv_label}"
                    )

                    if self._events:
                        await self._events.emit(
                            account_idx,
                            {
                                "event": "bot_online",
                                "wxid": wxid,
                                "sync_mode": "events_ws"
                                if events_ws_enabled()
                                else DEFAULT_MSG_SYNC_MODE,
                                "message": f"JSON 账号已上线（收消息={recv_label}）",
                            },
                        )

                    hold = asyncio.get_running_loop().create_future()
                    await hold
                except asyncio.CancelledError:
                    bot_logger.info(f"【{remark}】JSON 账号已停止")
                    raise
                except Exception as e:
                    bot_logger.exception(f"【{remark}】JSON 账号运行异常: {e}")
                    self._resolve_json_ready_future(
                        account_idx, JsonImportError(str(e))
                    )
                finally:
                    if use_events_ws:
                        await unsubscribe_events_ws()
                    if wxid:
                        await notify_bot_offline(wxid)
                        await unregister_online_client(wxid)
        finally:
            log_account_ctx.reset(ctx_token)
            self._json_ready_futures.pop(account_idx, None)
