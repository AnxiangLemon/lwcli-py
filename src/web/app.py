"""
LWAPI 运维台：aiohttp 应用定义与 REST / WebSocket 路由。

提供账号 CRUD、启停机器人、按备注读当日日志尾、插件启用列表读写，
以及按账号下标的 WS 通道用于推送扫码与登录状态（与 BotService 内 emit 对接）。
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from aiohttp import web, WSMsgType
from loguru import logger

from src.account_loader import account_slot_key, load_accounts_safe, save_accounts
from src.plugins.registry import REGISTRY, list_plugin_specs
from src.plugins.settings import load_enabled_ids, save_enabled_ids
from src.runtime.account_events import AccountEventHub
from src.services.bot_service import BotService
from src.utils import read_account_today_log_tail, setup_logger

STATIC_DIR = Path(__file__).parent / "static"


class AdminWebApp:
    """组装 EventHub、BotService 与 aiohttp 路由的运维台应用对象。"""

    def __init__(self) -> None:
        self.account_events = AccountEventHub()
        self.bot_service = BotService(account_events=self.account_events)
        setup_logger("web")

    def build(self) -> web.Application:
        app = web.Application()
        app.add_routes(
            [
                web.static("/static", str(STATIC_DIR)),
                web.get("/", self.index),
                web.get("/api/accounts", self.api_accounts),
                web.post("/api/accounts", self.api_account_create),
                web.put("/api/accounts/{idx}", self.api_account_update),
                web.delete("/api/accounts/{idx}", self.api_account_delete),
                web.get("/api/accounts/{idx}/log", self.api_account_log),
                web.get("/ws/account/{idx}", self.ws_account),
                web.post("/api/accounts/{idx}/start", self.api_start_one),
                web.post("/api/accounts/{idx}/stop", self.api_stop_one),
                web.post("/api/start-all", self.api_start_all),
                web.get("/api/plugins", self.api_plugins_get),
                web.put("/api/plugins", self.api_plugins_put),
            ]
        )
        return app

    async def index(self, request: web.Request) -> web.Response:
        return web.FileResponse(STATIC_DIR / "index.html")

    def _is_running(self, acc: dict) -> bool:
        return account_slot_key(acc) in set(self.bot_service.running_slot_keys())

    async def api_accounts(self, request: web.Request) -> web.Response:
        accounts = load_accounts_safe()
        running = set(self.bot_service.running_slot_keys())
        pending = self.bot_service.login_pending_indices
        output = []
        for i, acc in enumerate(accounts):
            output.append(
                {
                    **acc,
                    "running": account_slot_key(acc) in running,
                    "pending_login": i in pending,
                }
            )
        return web.json_response({"accounts": output})

    async def api_account_log(self, request: web.Request) -> web.Response:
        idx = int(request.match_info["idx"])
        try:
            n = int(request.rel_url.query.get("lines", "50"))
        except ValueError:
            n = 50
        accounts = load_accounts_safe()
        if idx < 0 or idx >= len(accounts):
            return web.json_response({"error": "账号不存在"}, status=404)
        acc = accounts[idx]
        remark = (acc.get("remark") or "").strip() or (acc.get("device_id") or "")[:8]
        payload = read_account_today_log_tail(remark, lines=n)
        return web.json_response(payload)

    async def api_account_create(self, request: web.Request) -> web.Response:
        try:
            body = await request.json()
        except json.JSONDecodeError:
            return web.json_response({"error": "无效 JSON"}, status=400)
        device_id = (body.get("device_id") or "").strip()
        if not device_id:
            return web.json_response({"error": "device_id 必填"}, status=400)
        remark = (body.get("remark") or "").strip() or device_id[:8]
        acc = {
            "device_id": device_id,
            "wxid": (body.get("wxid") or "").strip(),
            "remark": remark,
            "proxy": body.get("proxy"),
        }
        accounts = load_accounts_safe()
        accounts.append(acc)
        save_accounts(accounts)
        return web.json_response({"ok": True, "index": len(accounts) - 1})

    async def api_account_update(self, request: web.Request) -> web.Response:
        idx = int(request.match_info["idx"])
        try:
            body = await request.json()
        except json.JSONDecodeError:
            return web.json_response({"error": "无效 JSON"}, status=400)
        accounts = load_accounts_safe()
        if idx < 0 or idx >= len(accounts):
            return web.json_response({"error": "账号不存在"}, status=404)
        if self._is_running(accounts[idx]):
            return web.json_response(
                {"error": "该账号机器人运行中，请先停止后再编辑"}, status=409
            )
        if idx in self.bot_service.login_pending_indices:
            return web.json_response(
                {"error": "该账号正在登录中，请稍后再编辑"}, status=409
            )
        if "device_id" in body:
            accounts[idx]["device_id"] = str(body["device_id"]).strip()
        if "wxid" in body:
            accounts[idx]["wxid"] = str(body.get("wxid") or "").strip()
        if "remark" in body:
            accounts[idx]["remark"] = str(body.get("remark") or "").strip()
        if "proxy" in body:
            accounts[idx]["proxy"] = body.get("proxy")
        save_accounts(accounts)
        return web.json_response({"ok": True})

    async def api_account_delete(self, request: web.Request) -> web.Response:
        idx = int(request.match_info["idx"])
        accounts = load_accounts_safe()
        if idx < 0 or idx >= len(accounts):
            return web.json_response({"error": "账号不存在"}, status=404)
        if self._is_running(accounts[idx]):
            return web.json_response(
                {"error": "该账号机器人运行中，请先停止后再删除"}, status=409
            )
        if idx in self.bot_service.login_pending_indices:
            return web.json_response(
                {"error": "该账号正在登录中，请稍后再删除"}, status=409
            )
        accounts.pop(idx)
        save_accounts(accounts)
        return web.json_response({"ok": True})

    async def ws_account(self, request: web.Request) -> web.WebSocketResponse:
        idx = int(request.match_info["idx"])
        ws = web.WebSocketResponse(heartbeat=30)
        await ws.prepare(request)
        await self.account_events.register(idx, ws)
        try:
            while True:
                try:
                    msg = await ws.receive()
                except asyncio.CancelledError:
                    # SIGINT / 优雅退出：避免 CancelledError 冒泡到 aiohttp 协议层触发 InvalidStateError
                    break
                if msg.type in (WSMsgType.CLOSE, WSMsgType.ERROR, WSMsgType.CLOSED):
                    break
        finally:
            await self.account_events.unregister(idx, ws)
            if not ws.closed:
                await ws.close()
        return ws

    async def api_start_one(self, request: web.Request) -> web.Response:
        idx = int(request.match_info["idx"])
        accounts = load_accounts_safe()
        if idx < 0 or idx >= len(accounts):
            return web.json_response({"error": "账号不存在"}, status=404)
        account = accounts[idx]
        await self.bot_service.start_one(account, accounts, idx)
        return web.json_response({"ok": True})

    async def api_stop_one(self, request: web.Request) -> web.Response:
        idx = int(request.match_info["idx"])
        accounts = load_accounts_safe()
        if idx < 0 or idx >= len(accounts):
            return web.json_response({"error": "账号不存在"}, status=404)
        stopped = await self.bot_service.stop_for_account(accounts[idx])
        return web.json_response({"ok": True, "stopped": stopped})

    async def api_start_all(self, request: web.Request) -> web.Response:
        accounts = load_accounts_safe()
        await self.bot_service.start_all(accounts)
        return web.json_response({"ok": True, "count": len(accounts)})

    async def api_plugins_get(self, request: web.Request) -> web.Response:
        specs = list_plugin_specs()
        return web.json_response(
            {
                "plugins": [
                    {
                        "id": p.id,
                        "title": p.title,
                        "description": p.description,
                        "version": p.version,
                        "author": p.author,
                    }
                    for p in specs
                ],
                "enabled": load_enabled_ids(),
            }
        )

    async def api_plugins_put(self, request: web.Request) -> web.Response:
        try:
            body = await request.json()
        except json.JSONDecodeError:
            return web.json_response({"error": "无效 JSON"}, status=400)
        raw = body.get("enabled")
        if not isinstance(raw, list):
            return web.json_response({"error": "enabled 须为字符串 id 数组"}, status=400)
        ids = [str(x).strip() for x in raw if str(x).strip()]
        unknown = [i for i in ids if i not in REGISTRY]
        if unknown:
            return web.json_response(
                {"error": "未知插件 id", "unknown": unknown},
                status=400,
            )
        # 去重且保持前端传入顺序
        seen: set[str] = set()
        ordered: list[str] = []
        for i in ids:
            if i in seen:
                continue
            seen.add(i)
            ordered.append(i)
        save_enabled_ids(ordered)
        return web.json_response({"ok": True, "enabled": ordered})


def create_app() -> web.Application:
    return AdminWebApp().build()
