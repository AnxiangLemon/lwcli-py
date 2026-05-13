from __future__ import annotations

from typing import Dict, List

from src.plugins.builtin_debug_types import (
    PLUGIN_DESCRIPTION as _DBG_DESC,
    PLUGIN_ID as _DBG_ID,
    PLUGIN_TITLE as _DBG_TITLE,
    handle as _debug_handle,
)
from src.plugins.builtin_demo_replies import (
    PLUGIN_DESCRIPTION as _DEMO_DESC,
    PLUGIN_ID as _DEMO_ID,
    PLUGIN_TITLE as _DEMO_TITLE,
    handle as _demo_handle,
)
from src.plugins.types import PluginSpec

# 展示顺序（与是否启用无关）
_ALL: tuple[PluginSpec, ...] = (
    PluginSpec(
        id=_DEMO_ID,
        title=_DEMO_TITLE,
        description=_DEMO_DESC,
        handle=_demo_handle,
    ),
    PluginSpec(
        id=_DBG_ID,
        title=_DBG_TITLE,
        description=_DBG_DESC,
        handle=_debug_handle,
    ),
)

REGISTRY: Dict[str, PluginSpec] = {p.id: p for p in _ALL}


def list_plugin_specs() -> List[PluginSpec]:
    return list(_ALL)


def resolve_handlers(enabled_ids: List[str]) -> List[PluginSpec]:
    """按 enabled_ids 顺序解析为已注册插件（跳过未知 id）。"""
    seen: set[str] = set()
    out: List[PluginSpec] = []
    for pid in enabled_ids:
        if pid in seen:
            continue
        seen.add(pid)
        spec = REGISTRY.get(pid)
        if spec:
            out.append(spec)
    return out
