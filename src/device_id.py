"""
accounts.json 中 device_id 字段存 clientUuid 种子；规范化与校验（仅保证非空）。
服务端 DeviceId 另存 archived_device_id，不走本模块。
"""

from __future__ import annotations


def normalize_device_id(value: str) -> str:
    """去除首尾空白。"""
    return (value or "").strip()


def device_id_error_message(device_id: str) -> str | None:
    """
    校验 uuid（clientUuid 种子）；合法返回 None，否则返回中文错误说明。
    """
    if not normalize_device_id(device_id):
        return "uuid 不能为空"
    return None
