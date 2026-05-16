"""
公共插件：文本消息小工具（帮助 / 时间 / 心跳检测 + 可选 DEBUG 字段摘要）。

启用方式：运维台「插件管理」勾选 ``demo_helper`` 并保存（或写入 ``config/plugins.json`` 的 ``enabled`` 数组）。
"""

from __future__ import annotations

import re
from datetime import datetime
from zoneinfo import ZoneInfo

from loguru import logger

from lwapi import LwApiClient
from lwapi.models.msg import AddMsg, SyncMessageResponse

PLUGIN_ID = "demo_helper"
PLUGIN_TITLE = "Demo-自动回复"
PLUGIN_DESCRIPTION = (
    "私聊：帮助 / 时间 / ping；群聊：#命令 或 @机器人 + 命令。"
)
PLUGIN_VERSION = "1.0.0"
PLUGIN_AUTHOR = "LWAPI"

_TZ = ZoneInfo("Asia/Shanghai")
_GROUP_CMD_PREFIX = "#"
_NOTIFY_ALL = "notify@all"
_ATUSERLIST_CDATA_RE = re.compile(
    r"<atuserlist>\s*<!\[CDATA\[(?P<cdata>.*?)\]\]>\s*</atuserlist>",
    re.IGNORECASE | re.DOTALL,
)


def _safe_str(s: object | None, *, max_len: int = 120) -> str:
    if s is None:
        return ""
    text = str(s).replace("\r", " ").replace("\n", "↵")
    if len(text) > max_len:
        return text[: max_len - 3] + "..."
    return text


def _parse_atuserlist(msg_source: str | None) -> list[str]:
    if not msg_source:
        return []
    m = _ATUSERLIST_CDATA_RE.search(msg_source)
    if not m:
        return []
    inner = (m.group("cdata") or "").strip()
    if not inner:
        return []
    return [p.strip() for p in inner.split(",") if p.strip()]


def _ascii_suffix_cmd_ok(before_lower: str, needle_lower: str) -> bool:
    if not before_lower.endswith(needle_lower):
        return False
    prev = before_lower[: -len(needle_lower)]
    if not prev:
        return True
    ch = prev[-1]
    return not ("a" <= ch <= "z" or ch == "_")


def _find_trailing_command(body: str) -> str | None:
    b = body.strip()
    if not b:
        return None
    bl = b.lower()
    pairs = [
        ("帮助", "帮助"),
        ("help", "help"),
        ("时间", "时间"),
        ("time", "time"),
        ("ping", "ping"),
    ]
    for nlow, canonical in pairs:
        if canonical in ("帮助", "时间"):
            if not bl.endswith(nlow):
                continue
            prev = bl[: -len(nlow)]
            if prev and "\u4e00" <= prev[-1] <= "\u9fff":
                continue
            return canonical
        if _ascii_suffix_cmd_ok(bl, nlow):
            return canonical
    return None


def _parse_group_sender_and_body(raw: str) -> tuple[str | None, str]:
    text = (raw or "").strip()
    if not text:
        return None, ""
    m = re.match(r"^(?P<head>wxid_[^:\s]+)\s*:\s*(?P<body>.*)$", text, flags=re.DOTALL)
    if m:
        return m.group("head"), (m.group("body") or "").strip()
    return None, text


def _is_self_message(client_wxid: str, msg: AddMsg) -> bool:
    sender = (msg.fromUserName.string or "").strip()
    return bool(sender and sender == client_wxid)


def _debug_log_addmsg(wxid: str, msg: AddMsg) -> None:
    fu = msg.fromUserName.string
    tu = msg.toUserName.string
    ct = msg.content.string
    src = msg.msgSource
    src_preview = _safe_str(src, max_len=160) if src else ""
    at_users = _parse_atuserlist(src)
    logger.debug(
        "[{pid}] wxid={wxid} ← msgId={mid} fromUserName={fu} toUserName={tu} "
        "msgType={mt} content={ct!r} status={st} imgStatus={ist} "
        "imgBuf.len={ibl} createTime={ctm} msgSource.len={msl} msgSource~={srcp} "
        "atuserlist={atus} pushContent={pc!r} newMsgId={nmid} msgSeq={mseq}",
        pid=PLUGIN_ID,
        wxid=wxid,
        mid=msg.msgId,
        fu=fu,
        tu=tu,
        mt=msg.msgType,
        ct=_safe_str(ct, max_len=80),
        st=msg.status,
        ist=msg.imgStatus,
        ibl=msg.imgBuf.iLen if msg.imgBuf and msg.imgBuf.iLen is not None else 0,
        ctm=msg.createTime,
        msl=len(src or ""),
        srcp=src_preview,
        atus=at_users,
        pc=msg.pushContent,
        nmid=msg.newMsgId,
        mseq=msg.msgSeq,
    )


def _build_help_text(*, is_group: bool) -> str:
    prefix = (
        "群聊可用：① {_GROUP_CMD_PREFIX}命令，如 {_GROUP_CMD_PREFIX}时间；② @本机器人 + 命令（如 @昵称 时间）。"
        "回群时会按原消息的 @ 列表决定是否 @ 发言人或 @所有人。"
    ).format(_GROUP_CMD_PREFIX=_GROUP_CMD_PREFIX) if is_group else ""
    lines = [
        "【LWAPI 文本小工具】",
        "- 帮助：显示本说明",
        "- 时间：返回当前服务器时间（Asia/Shanghai）",
        "- ping：简单心跳，返回 pong（不含端到端网络测速）",
    ]
    if prefix:
        lines.insert(1, prefix)
    return "\n".join(lines)


async def handle(client: LwApiClient, resp: SyncMessageResponse) -> bool | None:
    wxid = client.wxid
    for msg in resp.addMsgs or []:
        if msg.msgType != 1:
            continue
        if _is_self_message(wxid, msg):
            continue
        _debug_log_addmsg(wxid, msg)
        raw_content = (msg.content.string or "").strip()
        from_id = (msg.fromUserName.string or "").strip()
        is_group = from_id.endswith("chatroom")
        at_list: list[str] = []
        speaker, body = _parse_group_sender_and_body(raw_content) if is_group else (None, raw_content)
        if is_group:
            at_list = _parse_atuserlist(msg.msgSource)
            hash_ok = body.strip().startswith(_GROUP_CMD_PREFIX)
            at_bot_ok = wxid in at_list
            if not hash_ok and not at_bot_ok:
                continue
            if hash_ok:
                user_cmd = body.strip()[len(_GROUP_CMD_PREFIX) :].strip().lower()
            else:
                user_cmd = _find_trailing_command(body)
                if user_cmd is None:
                    continue
        else:
            user_cmd = body.lower()
        if user_cmd in ("帮助", "help"):
            reply = _build_help_text(is_group=is_group)
        elif user_cmd in ("时间", "time"):
            now = datetime.now(_TZ).strftime("%Y-%m-%d %H:%M:%S %Z")
            reply = f"当前时间：{now}"
        elif user_cmd == "ping":
            reply = "pong"
        else:
            continue
        target = from_id
        at_user: str | None = None
        if is_group:
            if any(x == _NOTIFY_ALL for x in at_list):
                at_user = _NOTIFY_ALL
            elif speaker:
                at_user = speaker
        await client.msg.send_text_message(to_wxid=target, content=reply, at=at_user)
        return False  
    return None 