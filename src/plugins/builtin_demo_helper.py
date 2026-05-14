"""
内置插件：文本消息小工具（帮助 / 时间 / 心跳检测 + 可选 DEBUG 字段摘要）。

设计目标
--------
1. **日常可用**：好友私聊发「帮助」「时间」「ping」即得回复；群里支持 ``#`` 前缀 **或** ``@`` 当前机器人（依据 ``msgSource`` 里 ``atuserlist``）触发，减少无关自动回复。
2. **与协议字段对齐**：``lwapi.models.msg.AddMsg`` 中常见字段（msgId、fromUserName、msgType、
   content、createTime、msgSource 等）在 DEBUG 日志里按行打印，便于和你抓到的日志对照排查。
3. **安全默认**：忽略「自己发给自己账号」的同步回显，避免插件给自己再发消息形成环路。

消息体与日志里的对应关系（摘自 ``lwapi.models.msg.AddMsg``）
------------------------------------------------------------
- ``msgId``：客户端/同步层消息编号，同批里可能多条。
- ``fromUserName.string``：发送方 ID。私聊时为对方 wxid；群聊时为 ``xxx@chatroom``（群 ID）。
- ``toUserName.string``：接收方 ID。别人私聊你时通常是你的 wxid；群消息里也可能是群 ID 等，以实际同步为准。
- ``msgType``：类型码；``1`` 表示普通文本（与 ``builtin_demo_replies``、``builtin_debug_types`` 一致）。
- ``content.string``：正文。私聊多为纯文本；群聊常见 ``发言者wxid:\\n正文`` 形式，本插件会尝试剥掉前缀再匹配命令。
- ``status`` / ``imgStatus``：状态位；文本消息里常见固定值，排查图片/下载进度时更有用。
- ``imgBuf``：图片二进制缓存；文本消息里多为空（iLen=0）。
- ``createTime``：Unix 秒级时间戳。
- ``msgSource``：XML 扩展信息（签名、业务标记等）；体积可能较大，默认只打长度与预览。
  群内 ``@`` 时常见 ``<atuserlist><![CDATA[wxid_…]]></atuserlist>``，``@所有人`` 时为 ``<![CDATA[notify@all]]>``，本插件用其判断是否 ``@`` 到本号并决定回群时的 ``at`` 参数。
- ``newMsgId`` / ``msgSeq``：服务端侧新消息 ID、序列号；撤回、去重等场景会用到。

启用方式：运维台「插件管理」勾选 ``demo_helper`` 并保存（或写入 ``config/plugins.json`` 的 ``enabled`` 数组）。
"""

from __future__ import annotations

import re
from datetime import datetime
from zoneinfo import ZoneInfo

from loguru import logger

from lwapi import LwApiClient
from lwapi.models.msg import AddMsg, SyncMessageResponse

# ---------------------------------------------------------------------------
# 插件元数据（注册表 ``registry.py`` 会引用这些常量）
# ---------------------------------------------------------------------------

PLUGIN_ID = "demo_helper"
PLUGIN_TITLE = "Demo-自动回复"
PLUGIN_DESCRIPTION = (
    "私聊：帮助 / 时间 / ping；群聊：#命令 或 @机器人 + 命令。"
)

# 默认使用中国时区展示「时间」；若部署在海外可改为 UTC 或从配置读取。
_TZ = ZoneInfo("Asia/Shanghai")

# 群聊命令前缀：出现在剥离「wxid:」头后的正文行首，与「@ 到本号」二选一或同时满足均可触发。
_GROUP_CMD_PREFIX = "#"

# 微信「@所有人」在 atuserlist CDATA 中的固定串（与私聊 wxid 不会冲突）
_NOTIFY_ALL = "notify@all"

# 从 msgSource 中提取 <atuserlist> 的 CDATA（兼容大小写与空白）
_ATUSERLIST_CDATA_RE = re.compile(
    r"<atuserlist>\s*<!\[CDATA\[(?P<cdata>.*?)\]\]>\s*</atuserlist>",
    re.IGNORECASE | re.DOTALL,
)


def _safe_str(s: object | None, *, max_len: int = 120) -> str:
    """
    将可能为 None 的字符串安全缩略后写入日志，避免 None 或超长 XML 撑爆日志。
    """
    if s is None:
        return ""
    text = str(s).replace("\r", " ").replace("\n", "↵")
    if len(text) > max_len:
        return text[: max_len - 3] + "..."
    return text


def _parse_atuserlist(msg_source: str | None) -> list[str]:
    """
    从 ``msgSource`` XML 中解析 ``<atuserlist><![CDATA[...]]></atuserlist>``。

    常见取值：
    - 普通 ``@`` 成员：CDATA 内为单个 wxid，或多个 ``wxid_a,wxid_b``（逗号分隔，具体以后台为准）。
    - ``@所有人``：CDATA 内为固定串 ``notify@all``。

    若缺少该节点或解析失败，返回空列表（表示本条消息未携带结构化 @ 列表）。
    """
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
    """
    英文命令词贴在串尾时，要求前一个字符不是字母/下划线，避免 ``sometime`` 命中 ``time``。
    """
    if not before_lower.endswith(needle_lower):
        return False
    prev = before_lower[: -len(needle_lower)]
    if not prev:
        return True
    ch = prev[-1]
    return not ("a" <= ch <= "z" or ch == "_")


def _find_trailing_command(body: str) -> str | None:
    """
    在群正文（已去掉 ``wxid:`` 头）中，按「命令词在串尾」解析指令。

    用于 ``@昵称\\u2005时间`` 这类展示名与命令混排：整段不以 ``#`` 开头时，
    只要尾部能匹配 ``帮助`` / ``help`` / ``时间`` / ``time`` / ``ping`` 之一即视为命令。
    """
    b = body.strip()
    if not b:
        return None
    bl = b.lower()

    # (needle_lowercase_for_match, canonical_for_downstream_if)
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
            # 若命令前紧邻汉字，多为词内「时间」「帮助」等，避免「短时间」误触
            if prev and "\u4e00" <= prev[-1] <= "\u9fff":
                continue
            return canonical
        if _ascii_suffix_cmd_ok(bl, nlow):
            return canonical
    return None


def _parse_group_sender_and_body(raw: str) -> tuple[str | None, str]:
    """
    尝试从群聊文本里拆出「群内发言者 wxid」与「可见正文」。

    微信同步下来的群文本常见形态（简化）::

        wxid_xxxx:\\n
        用户真正输入的内容

    若不符合该形态，则视为整段都是正文，返回 (None, stripped_raw)。
    """
    text = (raw or "").strip()
    if not text:
        return None, ""

    # 第一段在冒号前且像 wxid 时，认为是「发言人:」头
    m = re.match(r"^(?P<head>wxid_[^:\s]+)\s*:\s*(?P<body>.*)$", text, flags=re.DOTALL)
    if m:
        return m.group("head"), (m.group("body") or "").strip()

    return None, text


def _is_self_message(client_wxid: str, msg: AddMsg) -> bool:
    """
    判断是否为自己账号发出的消息同步回来。

    说明：不同同步路径下「自己发消息」时 from/to 组合可能变化；这里采用保守判断——
    只要发送方 wxid 与当前登录 wxid 相同就跳过，避免自动回复套娃。
    """
    sender = (msg.fromUserName.string or "").strip()
    return bool(sender and sender == client_wxid)


def _debug_log_addmsg(wxid: str, msg: AddMsg) -> None:
    """
    在 DEBUG 级别打印与用户抓包类似的单行字段摘要（中文键意对照）。

    仅应在确认日志级别含 DEBUG 时启用；生产环境若只开 INFO 则不会输出。
    """
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


async def handle(client: LwApiClient, resp: SyncMessageResponse) -> None:
    """
    插件入口：与所有内置插件相同，签名固定为 ``(LwApiClient, SyncMessageResponse) -> None``。

    ``resp.addMsgs`` 为本轮同步批次内的新消息列表；需逐条判断类型与收发方后再动作。
    """
    wxid = client.wxid

    for msg in resp.addMsgs or []:
        # 非文本消息留给其它插件（如 debug_types）；本插件只处理文本。
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
            # 从 msgSource 取结构化 @ 列表（与正文里展示的 @昵称 独立，以后台为准）
            at_list = _parse_atuserlist(msg.msgSource)
            hash_ok = body.strip().startswith(_GROUP_CMD_PREFIX)
            at_bot_ok = wxid in at_list
            # 「#」与「@ 到本号」任一满足即可进入命令解析；仅 @其他人 不会触发
            if not hash_ok and not at_bot_ok:
                continue
            if hash_ok:
                # 与旧版一致：去掉行首 # 后整段视为命令（再 lower，便于英文）
                user_cmd = body.strip()[len(_GROUP_CMD_PREFIX) :].strip().lower()
            else:
                user_cmd = _find_trailing_command(body)
                if user_cmd is None:
                    continue
        else:
            # 私聊：整段即用户输入
            user_cmd = body.lower()

        # 统一成小写关键字匹配（中文命令仍用 lower 后与英文 help/ping 并列判断）
        if user_cmd in ("帮助", "help"):
            reply = _build_help_text(is_group=is_group)
        elif user_cmd in ("时间", "time"):
            now = datetime.now(_TZ).strftime("%Y-%m-%d %H:%M:%S %Z")
            reply = f"当前时间：{now}"
        elif user_cmd == "ping":
            reply = "pong"
        else:
            continue

        # 回复目标：私聊回对方 wxid；群聊回到群 ID（from_id 即为群 room id）
        target = from_id
        at_user: str | None = None
        if is_group:
            # 若原消息含 @所有人，回执同样 @所有人；否则尽量 @ 发言人（解析自 content 头）
            if any(x == _NOTIFY_ALL for x in at_list):
                at_user = _NOTIFY_ALL
            elif speaker:
                at_user = speaker

        await client.msg.send_text_message(to_wxid=target, content=reply, at=at_user)
