"""
插件启用列表的持久化与缓存：读写 config/plugins.json。

enabled 为字符串 id 数组，顺序即消息处理时插件执行顺序；文件 mtime 变化后
load_enabled_ids 会自动失效缓存，便于运维台保存后下一轮消息即生效。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List

from src.utils import atomic_write_json, logger

PLUGIN_CONFIG = Path("config/plugins.json")
DEFAULT_ENABLED = ["demo_replies"]

_mtime: float | None = None
_cached_enabled: List[str] | None = None


def _ensure_file() -> None:
    """首次使用时若不存在则写入默认启用列表。"""
    if PLUGIN_CONFIG.exists():
        return
    PLUGIN_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_json(PLUGIN_CONFIG, {"enabled": DEFAULT_ENABLED})
    logger.info(f"已创建默认插件配置 {PLUGIN_CONFIG}")


def invalidate_plugin_settings_cache() -> None:
    """保存配置后调用，强制下次重新读盘（亦可依赖 mtime 自然失效）。"""
    global _mtime, _cached_enabled
    _mtime = None
    _cached_enabled = None


def load_enabled_ids() -> List[str]:
    """按配置文件顺序返回已启用插件 id（带 mtime 缓存，便于热更新）。"""
    global _mtime, _cached_enabled
    _ensure_file()
    try:
        m = PLUGIN_CONFIG.stat().st_mtime
    except OSError:
        return list(DEFAULT_ENABLED)
    if _cached_enabled is not None and _mtime == m:
        return list(_cached_enabled)
    try:
        raw = json.loads(PLUGIN_CONFIG.read_text(encoding="utf-8"))
        ids = raw.get("enabled") if isinstance(raw, dict) else None
        if not isinstance(ids, list):
            ids = list(DEFAULT_ENABLED)
        out = [str(x).strip() for x in ids if str(x).strip()]
    except (json.JSONDecodeError, OSError) as e:
        logger.warning(f"读取 {PLUGIN_CONFIG} 失败，使用默认插件列表: {e}")
        out = list(DEFAULT_ENABLED)
    _mtime = m
    _cached_enabled = out
    return list(out)


def save_enabled_ids(ids: List[str]) -> None:
    """覆盖写入启用列表并清空缓存。"""
    atomic_write_json(PLUGIN_CONFIG, {"enabled": ids})
    invalidate_plugin_settings_cache()
