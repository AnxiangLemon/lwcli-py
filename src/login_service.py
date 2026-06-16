"""
微信登录流程封装（缓存二次登录 + 二维码登录）。

本仓库主入口为 Web 运维台：二维码阶段必须通过 emit 回调把 UUID、图片等
推送到前端 WebSocket；不再支持纯终端 ASCII 扫码。

若未传入 emit 且需要扫码，将抛出明确错误（请从网页启动并连接事件通道，
或预先在 accounts.json 中配置有效 wxid）。
"""

from __future__ import annotations

from typing import Awaitable, Callable, Optional, Tuple

from lwapi.exceptions import LoginError
from lwapi.models.login import ProxyInfo

from .services.qr_render import weixin_qr_png_base64, weixin_scan_url
from .utils import logger as root_logger

EmitFn = Callable[[dict], Awaitable[None]]


SESSION_IMPORT_KEYS = (
    "pid",
    "UIN",
    "wxid",
    "PSKAccessKey",
    "EarlyDataPart",
    "SharedKey",
    "Cookie",
    "SessionKey",
    "ClientVer",
    "DeviceId",
    "DeviceType",
    "Host",
)

# ImportUser 上报前账号内必须具备的字段（DeviceType / Host 有默认值）
IMPORT_USER_REQUIRED_FIELDS = (
    "wxid",
    "UIN",
    "ClientVer",
    "DeviceId",
    "SessionKey",
    "Cookie",
    "SharedKey",
    "EarlyDataPart",
    "PSKAccessKey",
)

# 连接失败时清除的会话字段（含旧版 camelCase 兼容键）
SESSION_CLEAR_KEYS = SESSION_IMPORT_KEYS + (
    "sessionKey",
    "sharedKey",
    "cookie",
    "host",
)

_SESSION_FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "pid": ("pid",),
    "UIN": ("UIN",),
    "wxid": ("wxid",),
    "PSKAccessKey": ("PSKAccessKey",),
    "EarlyDataPart": ("EarlyDataPart",),
    "SharedKey": ("SharedKey", "sharedKey"),
    "Cookie": ("Cookie", "cookie"),
    "SessionKey": ("SessionKey", "sessionKey"),
    "ClientVer": ("ClientVer",),
    "DeviceId": ("DeviceId", "device_id"),
    "DeviceType": ("DeviceType", "deviceType"),
    "Host": ("Host", "host"),
}

NEED_REFRESH_JSON_HINT = "请重新获取 JSON 数据"


def normalize_login_mode(mode: str) -> str:
    """返回 ``local``（本机 MMTLS）、``remote``（服务端直连）或 ``json``（外部已登录会话）。"""
    m = (mode or "").strip().lower()
    if m in ("local", "relay"):
        return "local"
    if m == "json":
        return "json"
    return "remote"


def extract_session_import_fields(body: dict) -> dict:
    """从请求体提取 JSON 导入会话字段，规范为服务端字段名。"""
    return normalize_session_fields(body)


def normalize_session_fields(body: dict) -> dict:
    """将粘贴/存储的 JSON 规范为服务端字段名（兼容旧 camelCase）。"""
    out: dict = {}
    if not isinstance(body, dict):
        return out
    for key in SESSION_IMPORT_KEYS:
        val = _account_field_raw(body, key)
        if val is None:
            continue
        if isinstance(val, str) and not val.strip():
            continue
        out[key] = val
    return out


DEFAULT_IMPORT_DEVICE_TYPE = "UnifiedPCWindows 11 x86_64"
DEFAULT_IMPORT_HOST = "szshort.weixin.qq.com"


def _account_field_raw(account: dict, key: str):
    aliases = _SESSION_FIELD_ALIASES.get(key, (key,))
    for alias in aliases:
        if alias not in account:
            continue
        val = account[alias]
        if val is None:
            continue
        if isinstance(val, str) and not val.strip():
            continue
        return val
    return None


def _account_field_value(account: dict, key: str) -> str:
    val = _account_field_raw(account, key)
    if val is None:
        return ""
    return str(val).strip()


def validate_import_user_account(account: dict) -> list[str]:
    """返回 ImportUser 前缺失的必填字段名列表。"""
    missing: list[str] = []
    for key in IMPORT_USER_REQUIRED_FIELDS:
        if not _account_field_value(account, key):
            missing.append(key)
    return missing


def format_import_user_error(message: str) -> str:
    msg = (message or "ImportUser 失败").strip()
    if NEED_REFRESH_JSON_HINT not in msg:
        msg = f"{msg}，{NEED_REFRESH_JSON_HINT}"
    return msg


def clear_session_import_fields(acc: dict) -> bool:
    """清空会话 JSON 字段，保留账号列表基本信息（wxid、备注、头像等）。"""
    changed = False
    for key in SESSION_CLEAR_KEYS:
        if key in acc:
            del acc[key]
            changed = True
    if acc.get("device_id"):
        acc["device_id"] = ""
        changed = True
    if acc.pop("import_connected", None) is not None:
        changed = True
    return changed


def build_import_user_payload(account: dict) -> dict:
    """将账号配置组装为 LwApi ``POST /api/Login/ImportUser`` 请求体。"""
    missing = validate_import_user_account(account)
    if missing:
        raise ValueError(NEED_REFRESH_JSON_HINT)

    wxid = _account_field_value(account, "wxid")
    device_id = _account_field_value(account, "DeviceId")
    session_key = _account_field_value(account, "SessionKey")
    shared_key = _account_field_value(account, "SharedKey")
    cookie = _account_field_value(account, "Cookie")

    payload: dict = {
        "wxid": wxid,
        "UIN": _account_field_raw(account, "UIN"),
        "ClientVer": _account_field_raw(account, "ClientVer"),
        "DeviceId": device_id,
        "DeviceType": str(
            _account_field_raw(account, "DeviceType") or DEFAULT_IMPORT_DEVICE_TYPE
        ).strip(),
        "Host": str(
            _account_field_raw(account, "Host") or DEFAULT_IMPORT_HOST
        ).strip(),
        "SessionKey": session_key,
        "Cookie": cookie,
        "SharedKey": shared_key,
        "EarlyDataPart": _account_field_raw(account, "EarlyDataPart"),
        "PSKAccessKey": _account_field_raw(account, "PSKAccessKey"),
    }
    pid = _account_field_raw(account, "pid")
    if pid is not None:
        payload["pid"] = pid
    return {k: v for k, v in payload.items() if v is not None and v != ""}


def _protobuf_string(val) -> str:
    """兼容 ``{"string": "..."}`` 与纯字符串。"""
    if val is None:
        return ""
    if isinstance(val, dict):
        return str(val.get("string") or "").strip()
    return str(val).strip()


def parse_import_user_profile(data: dict) -> tuple[str, str]:
    """从 ImportUser 响应提取 nickname、avatar_url。"""
    if not isinstance(data, dict):
        return "", ""
    user_info = data.get("userInfo")
    user_ext = data.get("userInfoExt")
    user_info = user_info if isinstance(user_info, dict) else {}
    user_ext = user_ext if isinstance(user_ext, dict) else {}

    nickname = _protobuf_string(user_info.get("nickName"))
    avatar_url = str(
        user_ext.get("bigHeadImgUrl")
        or user_ext.get("smallHeadImgUrl")
        or user_info.get("bigHeadImgUrl")
        or user_info.get("smallHeadImgUrl")
        or ""
    ).strip()
    return nickname, avatar_url


def import_user_response_ok(data: dict) -> bool:
    base = data.get("baseResponse") if isinstance(data, dict) else None
    if not isinstance(base, dict):
        return True
    ret = base.get("ret")
    return ret is None or ret == 0


def apply_import_user_profile(acc: dict, data: dict) -> bool:
    """将 ImportUser 响应中的昵称与头像写入账号配置，有变化时返回 True。"""
    if not import_user_response_ok(data):
        return False
    nickname, avatar_url = parse_import_user_profile(data)
    changed = False
    if nickname and acc.get("nickname") != nickname:
        acc["nickname"] = nickname
        changed = True
    if avatar_url and acc.get("avatar_url") != avatar_url:
        acc["avatar_url"] = avatar_url
        changed = True
    return changed


class LoginService:
    """组合 LwApiClient.login 的若干步骤，供 BotService 在单账号协程里调用。"""

    def __init__(self, client, device_id: str, proxy=None, remark: str = ""):
        self.client = client
        self.device_id = device_id
        self.proxy = ProxyInfo(**proxy) if proxy else None
        self.remark = remark

    async def login(
        self,
        saved_wxid: str = "",
        emit: Optional[EmitFn] = None,
    ) -> Tuple[str, str]:
        """
        先尝试缓存 wxid 二次登录；失败则拉二维码，经 emit 流式上报状态直至成功。

        emit 为 None 时：仅当二次登录已成功时才能继续；否则无法展示二维码。
        """
        login = self.client.login

        if saved_wxid:
            self.client.set_wxid(saved_wxid)
            if await login.sec_auto_login():
                root_logger.success(f"【{self.remark}】二次登录成功 → {saved_wxid}")
                if emit:
                    await emit(
                        {
                            "event": "sec_auto_ok",
                            "wxid": saved_wxid,
                            "message": "已使用本地缓存登录，无需扫码",
                        }
                    )
                return saved_wxid, self.device_id

        root_logger.info(f"【{self.remark}】正在获取二维码...")
        qr = await login.get_qr_code(self.device_id, self.proxy)

        if not emit:
            raise LoginError(
                "需要扫码登录但未提供事件推送（emit）。请从运维台启动本账号并保持 "
                "WebSocket 已连接，或在 config/accounts.json 中填入有效 wxid 后重试。"
            )

        scan_url = (qr.qr_url or "").strip() or weixin_scan_url(qr.uuid)
        png_b64 = weixin_qr_png_base64(qr.uuid)
        await emit(
            {
                "event": "qr_ready",
                "uuid": qr.uuid,
                "qr_base64": png_b64,
                "qr_url": scan_url,
                "device_id": qr.device_id,
            }
        )
        wxid: Optional[str] = None
        async for ev in login.stream_qr_status(
            qr.uuid,
            interval=3.0,
            timeout=300.0,
        ):
            await emit(ev)
            if ev.get("event") == "success":
                wxid = ev.get("wxid")
                break
            if ev.get("event") == "error":
                raise LoginError(
                    ev.get("message") or str(ev.get("code") or "二维码登录失败"),
                    reason=str(ev.get("code") or ""),
                )
        if not wxid:
            raise LoginError("登录未完成或已中断")

        self.client.set_wxid(wxid)
        root_logger.success(f"【{self.remark}】登录成功！wxid = {wxid}")
        return wxid, qr.device_id
