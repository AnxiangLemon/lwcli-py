"""
AI 智能回复插件（默认对接 DeepSeek OpenAI 兼容接口）。

在运维台配置 API Key 与模型后，私聊文本将自动走大模型回复；群聊可按 @ 机器人 / #前缀 触发。
配置保存后热更新，无需重启。
"""

from __future__ import annotations

import re
from typing import Any

import httpx
from loguru import logger

from lwapi import LwApiClient
from lwapi.models.msg import SyncMessageResponse
from src.plugins.bot_tasks import spawn_bot_task
from src.plugins.config import load_plugin_settings

PLUGIN_ID = "ai_reply"
PLUGIN_TITLE = "AI 智能回复"
PLUGIN_DESCRIPTION = (
    "对接 DeepSeek 等大模型 API；支持私聊/群聊 wxid 白名单、私聊/群聊分别配置系统提示词。"
)
PLUGIN_VERSION = "1.0.0"
PLUGIN_AUTHOR = "LWAPI"
PLUGIN_ICON = "🤖"
PLUGIN_SETTINGS_PANEL = "panels/ai_reply"

_GROUP_CMD_PREFIX = "#"
_ATUSERLIST_CDATA_RE = re.compile(
    r"<atuserlist>\s*<!\[CDATA\[(?P<cdata>.*?)\]\]>\s*</atuserlist>",
    re.IGNORECASE | re.DOTALL,
)

# 进程内多轮对话缓存：(bot_wxid, peer_wxid) -> messages
_history: dict[tuple[str, str], list[dict[str, str]]] = {}


def _cfg_bool(cfg: dict[str, Any], key: str, default: bool = True) -> bool:
    val = cfg.get(key)
    if val is None:
        return default
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return val.strip().lower() in ("1", "true", "yes", "on")
    return bool(val)


def _cfg_float(cfg: dict[str, Any], key: str, default: float) -> float:
    try:
        return float(cfg.get(key, default))
    except (TypeError, ValueError):
        return default


def _cfg_int(cfg: dict[str, Any], key: str, default: int) -> int:
    try:
        return int(cfg.get(key, default))
    except (TypeError, ValueError):
        return default


def _effective_api_key(cfg: dict[str, Any]) -> str:
    return (cfg.get("api_key") or "").strip()


def _api_base(cfg: dict[str, Any]) -> str:
    base = (cfg.get("base_url") or "https://api.deepseek.com").strip().rstrip("/")
    if base.endswith("/v1"):
        base = base[:-3]
    return base


def _models_endpoint_candidates(cfg: dict[str, Any]) -> list[str]:
    """OpenAI 兼容服务模型列表常见路径（优先 /v1/models）。"""
    base = _api_base(cfg)
    seen: set[str] = set()
    out: list[str] = []
    for path in ("/v1/models", "/models"):
        url = f"{base}{path}"
        if url not in seen:
            seen.add(url)
            out.append(url)
    return out


def _chat_endpoint(cfg: dict[str, Any]) -> str:
    if _cfg_bool(cfg, "use_full_url", False):
        url = (cfg.get("chat_url") or "").strip().rstrip("/")
        if url:
            return url
    base = _api_base(cfg)
    path = (cfg.get("chat_path") or "/v1/chat/completions").strip()
    if not path.startswith("/"):
        path = "/" + path
    return base + path


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


def _parse_group_sender_and_body(raw: str) -> tuple[str | None, str]:
    text = (raw or "").strip()
    if not text:
        return None, ""
    m = re.match(r"^(?P<head>wxid_[^:\s]+)\s*:\s*(?P<body>.*)$", text, flags=re.DOTALL)
    if m:
        return m.group("head"), (m.group("body") or "").strip()
    return None, text


_DEFAULT_SYSTEM_PROMPT = "你是一个友善、简洁的中文助手。"


def _parse_pipe_list(raw: object) -> set[str]:
    """解析 `a|b|c` 白名单；空字符串表示不限制。"""
    if raw is None:
        return set()
    text = str(raw).strip()
    if not text:
        return set()
    out: set[str] = set()
    for chunk in text.replace("\n", "|").split("|"):
        w = chunk.strip()
        if w:
            out.add(w)
    return out


def _allow_list_pass(cfg: dict[str, Any], key: str, peer_id: str) -> bool:
    """白名单字段为空则全部允许，否则 peer_id 须在列表中。"""
    allow = _parse_pipe_list(cfg.get(key))
    if not allow:
        return True
    return peer_id.strip() in allow


def _private_peer_allowed(cfg: dict[str, Any], peer_wxid: str) -> bool:
    return _allow_list_pass(cfg, "private_allow_wxids", peer_wxid)


def _group_chat_allowed(cfg: dict[str, Any], chatroom_id: str) -> bool:
    return _allow_list_pass(cfg, "group_allow_wxids", chatroom_id)


def _system_prompt_for(cfg: dict[str, Any], *, is_group: bool) -> str:
    if is_group:
        specific = (cfg.get("system_prompt_group") or "").strip()
    else:
        specific = (cfg.get("system_prompt_private") or "").strip()
    if specific:
        return specific
    return (cfg.get("system_prompt") or _DEFAULT_SYSTEM_PROMPT).strip()


def _strip_bot_mention(body: str, bot_wxid: str) -> str:
    """去掉群消息里 @机器人 的常见前缀，保留用户真实问题。"""
    b = body.strip()
    if not b:
        return b
    # 去掉开头 @xxx 空格（微信 pushContent 里常见昵称，这里只做简单空白切分）
    parts = b.split(None, 1)
    if len(parts) == 2 and parts[0].startswith("@"):
        return parts[1].strip()
    return b


def _should_reply(
    *,
    cfg: dict[str, Any],
    bot_wxid: str,
    from_id: str,
    body: str,
    is_group: bool,
    at_list: list[str],
) -> tuple[bool, str]:
    """判断是否触发 AI，并返回用于模型的用户文本。"""
    if not _cfg_bool(cfg, "enabled", True):
        return False, ""
    text = body.strip()
    if not text:
        return False, ""
    if is_group:
        if not _cfg_bool(cfg, "reply_group", True):
            return False, ""
        if not _group_chat_allowed(cfg, from_id):
            return False, ""
        trigger = (cfg.get("group_trigger") or "at_only").strip().lower()
        prefix = (cfg.get("group_prefix") or _GROUP_CMD_PREFIX).strip()
        if trigger == "always":
            user_text = text
        elif trigger == "prefix":
            if not text.startswith(prefix):
                return False, ""
            user_text = text[len(prefix) :].strip()
            if not user_text:
                return False, ""
        else:
            # at_only：须 @ 本机器人
            if bot_wxid not in at_list:
                return False, ""
            user_text = _strip_bot_mention(text, bot_wxid)
            if not user_text:
                return False, ""
        return True, user_text
    if not _cfg_bool(cfg, "reply_private", True):
        return False, ""
    if not _private_peer_allowed(cfg, from_id):
        return False, ""
    return True, text


def _history_key(bot_wxid: str, peer_wxid: str) -> tuple[str, str]:
    return bot_wxid, peer_wxid


def _get_history(bot_wxid: str, peer_wxid: str) -> list[dict[str, str]]:
    return list(_history.get(_history_key(bot_wxid, peer_wxid), []))


def _append_history(bot_wxid: str, peer_wxid: str, role: str, content: str, *, max_turns: int) -> None:
    if max_turns <= 0:
        return
    key = _history_key(bot_wxid, peer_wxid)
    hist = _history.setdefault(key, [])
    hist.append({"role": role, "content": content})
    cap = max(2, max_turns * 2)
    if len(hist) > cap:
        _history[key] = hist[-cap:]


def clear_chat_history(*, bot_wxid: str | None = None) -> int:
    """清空进程内多轮对话缓存；返回被移除的会话数（bot+联系人 维度）。"""
    if not bot_wxid:
        n = len(_history)
        _history.clear()
        return n
    bot_wxid = bot_wxid.strip()
    keys = [k for k in _history if k[0] == bot_wxid]
    for k in keys:
        del _history[k]
    return len(keys)


async def chat_completion(
    cfg: dict[str, Any],
    user_text: str,
    *,
    bot_wxid: str,
    peer_wxid: str,
    is_group: bool = False,
) -> str:
    api_key = _effective_api_key(cfg)
    if not api_key:
        raise ValueError("未配置 API Key")

    endpoint = _chat_endpoint(cfg)
    if not endpoint:
        raise ValueError("未配置请求地址")

    model = (cfg.get("model") or "").strip()
    if not model:
        raise ValueError("未配置模型（请先在设置页获取模型并选择后保存）")
    system_prompt = _system_prompt_for(cfg, is_group=is_group)
    temperature = _cfg_float(cfg, "temperature", 0.7)
    max_tokens = _cfg_int(cfg, "max_tokens", 1024)
    timeout = _cfg_float(cfg, "timeout_sec", 60.0)
    max_turns = _cfg_int(cfg, "max_context_turns", 6)

    messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]
    if _cfg_bool(cfg, "use_context", True) and max_turns > 0:
        messages.extend(_get_history(bot_wxid, peer_wxid))
    messages.append({"role": "user", "content": user_text})

    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False,
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(endpoint, json=payload, headers=headers)
        if resp.status_code >= 400:
            detail = resp.text[:500]
            raise RuntimeError(f"API HTTP {resp.status_code}: {detail}")
        data = resp.json()

    choices = data.get("choices") or []
    if not choices:
        raise RuntimeError("API 返回无 choices")
    msg = choices[0].get("message") or {}
    content = (msg.get("content") or "").strip()
    if not content:
        raise RuntimeError("API 返回空内容")
    if _cfg_bool(cfg, "use_context", True) and max_turns > 0 and bot_wxid != "__test__":
        _append_history(bot_wxid, peer_wxid, "user", user_text, max_turns=max_turns)
        _append_history(bot_wxid, peer_wxid, "assistant", content, max_turns=max_turns)
    return content


async def clear_context(cfg: dict[str, Any]) -> dict[str, Any]:
    """运维台「清空对话上下文」：清空本进程内全部多轮缓存。"""
    n = clear_chat_history()
    return {"ok": True, "cleared_sessions": n, "message": f"已清空 {n} 个联系人的对话上下文"}


async def test_settings(cfg: dict[str, Any]) -> dict[str, Any]:
    reply = await chat_completion(
        cfg,
        "请只回复：连接成功",
        bot_wxid="__test__",
        peer_wxid="__test__",
    )
    return {"ok": True, "message": reply[:200]}


def _merge_model_ids(*sources: object) -> list[str]:
    """合并多组模型 id，去重并保持顺序。"""
    seen: set[str] = set()
    out: list[str] = []
    for src in sources:
        if src is None:
            continue
        if isinstance(src, str):
            items = [src]
        elif isinstance(src, (list, tuple)):
            items = list(src)
        else:
            continue
        for raw in items:
            mid = str(raw).strip()
            if not mid or mid in seen:
                continue
            seen.add(mid)
            out.append(mid)
    return out


async def list_models(cfg: dict[str, Any]) -> dict[str, Any]:
    """GET /v1/models 或 /models（DeepSeek 等 OpenAI 兼容接口）。"""
    api_key = _effective_api_key(cfg)
    if not api_key:
        raise ValueError("未配置 API Key")
    timeout = _cfg_float(cfg, "timeout_sec", 60.0)
    headers = {"Authorization": f"Bearer {api_key}"}
    urls = _models_endpoint_candidates(cfg)
    cached = cfg.get("cached_model_ids")
    last_err = ""
    api_models: list[str] = []
    hit_url = ""
    async with httpx.AsyncClient(timeout=timeout) as client:
        for url in urls:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 404:
                last_err = f"{url} → 404"
                continue
            if resp.status_code >= 400:
                detail = resp.text[:400]
                raise RuntimeError(f"{url} → HTTP {resp.status_code}: {detail}")
            data = resp.json()
            raw = data.get("data") if isinstance(data, dict) else None
            if not isinstance(raw, list):
                last_err = f"{url} → 响应无 data 列表"
                continue
            for item in raw:
                if isinstance(item, dict):
                    mid = (item.get("id") or "").strip()
                    if mid:
                        api_models.append(mid)
            if not api_models:
                last_err = f"{url} → 模型列表为空"
                continue
            hit_url = url
            break
    if not api_models and not cached:
        raise RuntimeError(
            f"无法获取模型列表（已尝试: {', '.join(urls)}）"
            + (f"；{last_err}" if last_err else "")
            + "。请确认 Base URL 为 https://api.deepseek.com"
        )
    if api_models:
        models = _merge_model_ids(api_models)
    else:
        models = _merge_model_ids(cached)
    return {"ok": True, "models": models, "endpoint": hit_url or urls[0]}


async def _reply_task(
    client: LwApiClient,
    *,
    to_wxid: str,
    at_user: str | None,
    user_text: str,
    peer_for_history: str,
    is_group: bool,
) -> None:
    cfg = load_plugin_settings(PLUGIN_ID)
    bot_wxid = (client.wxid or "").strip()
    try:
        reply = await chat_completion(
            cfg,
            user_text,
            bot_wxid=bot_wxid,
            peer_wxid=peer_for_history,
            is_group=is_group,
        )
    except Exception as e:
        logger.warning(f"[{PLUGIN_ID}] 调用模型失败: {e}")
        if _cfg_bool(cfg, "reply_on_error", False):
            err_msg = (cfg.get("error_message") or "AI 暂时不可用，请稍后再试。").strip()
            reply = err_msg
        else:
            return
    try:
        await client.msg.send_text_message(to_wxid=to_wxid, content=reply, at=at_user)
        logger.info(f"[{PLUGIN_ID}] 已回复 {to_wxid}: {reply[:60]}...")
    except Exception:
        logger.exception(f"[{PLUGIN_ID}] 发送回复失败 to={to_wxid}")


async def handle(client: LwApiClient, resp: SyncMessageResponse) -> bool | None:
    cfg = load_plugin_settings(PLUGIN_ID)
    if not _effective_api_key(cfg):
        return None
    if not _cfg_bool(cfg, "enabled", True):
        return None

    bot_wxid = (client.wxid or "").strip()
    for msg in resp.addMsgs or []:
        if msg.msgType != 1:
            continue
        sender = (msg.fromUserName.string or "").strip()
        if sender == bot_wxid:
            continue

        raw_content = (msg.content.string or "").strip()
        from_id = sender
        is_group = from_id.endswith("chatroom")
        at_list: list[str] = []
        speaker: str | None = None
        body = raw_content

        if is_group:
            speaker, body = _parse_group_sender_and_body(raw_content)
            at_list = _parse_atuserlist(msg.msgSource)

        ok, user_text = _should_reply(
            cfg=cfg,
            bot_wxid=bot_wxid,
            from_id=from_id,
            body=body,
            is_group=is_group,
            at_list=at_list,
        )
        if not ok:
            continue

        target = from_id
        at_user: str | None = None
        peer_history = speaker if is_group and speaker else from_id
        if is_group and speaker:
            at_user = speaker

        spawn_bot_task(
            bot_wxid,
            _reply_task(
                client,
                to_wxid=target,
                at_user=at_user,
                user_text=user_text,
                peer_for_history=peer_history,
                is_group=is_group,
            ),
            name=f"{PLUGIN_ID}:chat",
        )
        return False
    return None
