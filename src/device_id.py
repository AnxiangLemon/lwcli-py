"""
device_id 规范化与校验（与运维台前端 index.html 规则一致）。
"""

from __future__ import annotations

import re

_DEVICE_ID_RE = re.compile(r"^[a-f0-9]{32}$")


def normalize_device_id(value: str) -> str:
    """去除首尾空白并转为小写。"""
    return (value or "").strip().lower()


def device_id_error_message(device_id: str) -> str | None:
    """
    校验 device_id；合法返回 None，否则返回中文错误说明。
    """
    did = normalize_device_id(device_id)
    if not did:
        return "device_id 不能为空"
    if len(did) != 32:
        return f"device_id 须为 32 位十六进制，当前 {len(did)} 位"
    if not _DEVICE_ID_RE.fullmatch(did):
        return "device_id 只能包含小写 a–f 与数字 0–9"
    return None
