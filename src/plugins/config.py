"""
各插件业务配置的读写与缓存（存于 config/plugins.json 的 settings 段）。

与 enabled 列表共用同一文件；mtime 变化后自动失效缓存，保存后无需重启进程。
"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict

from src.plugins.settings import PLUGIN_CONFIG, _ensure_file, invalidate_plugin_settings_cache
from src.utils import atomic_write_json, logger

_config_mtime: float | None = None
_cached_raw: Dict[str, Any] | None = None


def invalidate_plugin_config_cache() -> None:
    global _config_mtime, _cached_raw
    _config_mtime = None
    _cached_raw = None


def _load_raw() -> Dict[str, Any]:
    global _config_mtime, _cached_raw
    _ensure_file()
    try:
        m = PLUGIN_CONFIG.stat().st_mtime
    except OSError:
        return {}
    if _cached_raw is not None and _config_mtime == m:
        return deepcopy(_cached_raw)
    try:
        raw = json.loads(PLUGIN_CONFIG.read_text(encoding="utf-8"))
        data = raw if isinstance(raw, dict) else {}
    except (json.JSONDecodeError, OSError) as e:
        logger.warning(f"读取 {PLUGIN_CONFIG} 失败: {e}")
        data = {}
    _config_mtime = m
    _cached_raw = data
    return deepcopy(data)


def _save_raw(data: Dict[str, Any]) -> None:
    atomic_write_json(PLUGIN_CONFIG, data)
    invalidate_plugin_settings_cache()
    invalidate_plugin_config_cache()


def load_plugin_settings(plugin_id: str) -> Dict[str, Any]:
    """返回某插件的配置副本。"""
    raw = _load_raw()
    settings = raw.get("settings")
    if not isinstance(settings, dict):
        return {}
    block = settings.get(plugin_id)
    if not isinstance(block, dict):
        return {}
    return deepcopy(block)


_SECRET_FIELD_NAMES = frozenset({"api_key", "secret_key", "access_token"})
SECRET_MASK_DISPLAY = "****************"


def is_secret_placeholder(value: object) -> bool:
    """占位符或掩码（留空保存、不修改已存密钥）。"""
    if value is None:
        return True
    if not isinstance(value, str):
        return False
    s = value.strip()
    if not s:
        return True
    if s == SECRET_MASK_DISPLAY:
        return True
    return len(s) >= 6 and all(c in "*•●·." for c in s)


def mask_settings_for_api(settings: Dict[str, Any]) -> Dict[str, Any]:
    """API 响应中脱敏密钥字段（用 * 占位显示已配置）。"""
    out = deepcopy(settings)
    for name in _SECRET_FIELD_NAMES:
        if name in out and out[name]:
            out[f"{name}_configured"] = True
            out[name] = SECRET_MASK_DISPLAY
        elif name in out:
            out[f"{name}_configured"] = False
            out[name] = ""
    return out


def prepare_settings_patch(patch: Dict[str, Any]) -> Dict[str, Any]:
    """保存前处理：空值或掩码表示不修改原密钥。"""
    out = dict(patch)
    for name in _SECRET_FIELD_NAMES:
        if is_secret_placeholder(out.get(name)):
            out.pop(name, None)
    return out


def save_plugin_settings(plugin_id: str, patch: Dict[str, Any]) -> Dict[str, Any]:
    """合并写入插件配置，返回合并后的完整配置。"""
    raw = _load_raw()
    settings = raw.get("settings")
    if not isinstance(settings, dict):
        settings = {}
    current = settings.get(plugin_id)
    if not isinstance(current, dict):
        current = {}
    merged = {**current, **prepare_settings_patch(patch)}
    settings[plugin_id] = merged
    raw["settings"] = settings
    _save_raw(raw)
    return deepcopy(merged)
