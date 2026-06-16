"""EVENT_WS 收消息 → 在线 client → 插件链桥接。"""
from __future__ import annotations

from loguru import logger

from lwapi.events_parser import addmsg_to_sync_response
from lwapi.models.msg import AddMsg

from src.account_loader import load_accounts_safe
from src.plugins.chain import composite_message_handler
from src.runtime.client_registry import get_client, list_online_wxids


def _envelope_wxid(envelope: dict) -> str:
    for key in ("wxid", "Wxid", "botWxid"):
        val = str(envelope.get(key) or "").strip()
        if val:
            return val
    return ""


def _wxid_by_pid(pid) -> str:
    if pid is None or pid == "":
        return ""
    pid_s = str(pid).strip()
    for acc in load_accounts_safe():
        if str(acc.get("pid") or "").strip() == pid_s:
            return str(acc.get("wxid") or "").strip()
    return ""


async def resolve_bot_wxid(envelope: dict, msg: AddMsg) -> str | None:
    """从 EVENT_WS 信封或 AddMsg 推断接收消息的机器人 wxid。"""
    wxid = _envelope_wxid(envelope)
    if wxid:
        logger.debug(f"Events WS resolve wxid from envelope: {wxid}")
        return wxid

    wxid = _wxid_by_pid(envelope.get("pid"))
    if wxid:
        logger.debug(f"Events WS resolve wxid from pid={envelope.get('pid')}: {wxid}")
        return wxid

    online = set(await list_online_wxids())
    if not online:
        return None

    to_user = (msg.toUserName.string or "").strip()
    from_user = (msg.fromUserName.string or "").strip()

    if to_user in online:
        logger.debug(f"Events WS resolve wxid from toUserName: {to_user}")
        return to_user
    if from_user in online:
        logger.debug(f"Events WS resolve wxid from fromUserName: {from_user}")
        return from_user

    logger.debug(
        "Events WS 无法从 envelope/AddMsg 匹配在线 wxid "
        f"(online={sorted(online)}, from={from_user!r}, to={to_user!r})"
    )
    return None


async def events_plugin_handler(msg: AddMsg, envelope: dict) -> None:
    """将 EVENT_WS 单条消息交给已在线机器人的插件链处理。"""
    bot_wxid = await resolve_bot_wxid(envelope, msg)
    if not bot_wxid:
        return

    client = await get_client(bot_wxid)
    if client is None:
        logger.debug(f"Events WS bot {bot_wxid} 未在 client_registry，已忽略")
        return

    resp = addmsg_to_sync_response(msg)
    await composite_message_handler(client, resp)
