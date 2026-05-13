"""
内置消息插件注册表：聚合各 builtin_* 模块的元数据与处理函数。

新增插件时：编写新模块（PLUGIN_ID / TITLE / DESCRIPTION / handle），再在本文件
的 _ALL 元组中追加 PluginSpec；运维台会通过 GET /api/plugins 发现新条目。
"""

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

# 运维台列表展示顺序（与是否勾选启用无关）
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
    """返回所有已编译进进程的插件定义（供 API 与前端展示）。"""
    return list(_ALL)


def resolve_handlers(enabled_ids: List[str]) -> List[PluginSpec]:
    """按 enabled_ids 顺序解析为已注册插件（跳过未知 id、去重保留先出现的顺序）。"""
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
