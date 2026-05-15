"""
消息插件注册表：扫描 plugins/ 首层 lwplugin_*.py，供链式调用与运维台 API 使用。

仅加载文件名以 ``lwplugin_`` 开头的模块；子目录内的 .py 不参与扫描（可存放用户私有代码）。
启动时会在控制台打印已发现的插件 id 与名称。
"""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

from loguru import logger

from src.plugins.types import PluginSpec

PLUGIN_FILE_PREFIX = "lwplugin_"
_PLUGINS_DIR_ENV = "LWAPI_PLUGINS_DIR"
_DEFAULT_PLUGINS_DIR = Path("plugins")


def _plugins_dir() -> Path:
    override = os.environ.get(_PLUGINS_DIR_ENV, "").strip()
    if override:
        return Path(override)
    return _DEFAULT_PLUGINS_DIR


def _spec_from_module(module: object, *, source: str) -> Optional[PluginSpec]:
    pid = getattr(module, "PLUGIN_ID", None)
    if not pid or not isinstance(pid, str):
        logger.warning(f"插件模块 {source} 缺少 PLUGIN_ID，已跳过")
        return None
    handle = getattr(module, "handle", None)
    if handle is None or not callable(handle):
        logger.warning(f"插件模块 {source} 缺少可调用 handle，已跳过")
        return None
    title = getattr(module, "PLUGIN_TITLE", None) or pid
    desc = getattr(module, "PLUGIN_DESCRIPTION", None) or ""
    return PluginSpec(
        id=pid.strip(),
        title=str(title),
        description=str(desc),
        handle=handle,
        version=str(getattr(module, "PLUGIN_VERSION", "1.0.0")),
        author=str(getattr(module, "PLUGIN_AUTHOR", "") or ""),
    )


def _module_name_for_file(path: Path) -> str:
    return f"lwapi_plugin_{path.stem}"


def _load_plugins_from_dir() -> List[PluginSpec]:
    root = _plugins_dir()
    if not root.is_dir():
        return []

    specs: List[PluginSpec] = []
    seen_ids: set[str] = set()
    for path in sorted(root.glob(f"{PLUGIN_FILE_PREFIX}*.py")):
        if not path.is_file():
            continue
        mod_name = _module_name_for_file(path)
        spec_obj = importlib.util.spec_from_file_location(mod_name, path)
        if spec_obj is None or spec_obj.loader is None:
            logger.warning(f"无法加载插件 {path}")
            continue
        module = importlib.util.module_from_spec(spec_obj)
        sys.modules[mod_name] = module
        try:
            spec_obj.loader.exec_module(module)
        except Exception:
            logger.exception(f"加载插件失败: {path}")
            sys.modules.pop(mod_name, None)
            continue
        plugin_spec = _spec_from_module(module, source=str(path))
        if not plugin_spec:
            continue
        if plugin_spec.id in seen_ids:
            logger.warning(
                f"插件 id 重复，已忽略: {plugin_spec.id} ({plugin_spec.title})"
            )
            continue
        seen_ids.add(plugin_spec.id)
        specs.append(plugin_spec)
    return specs


def _print_discovered_plugins(specs: List[PluginSpec], *, root: Path) -> None:
    root_label = root.resolve()
    if not root.is_dir():
        print(f"[插件] 目录不存在，跳过扫描: {root_label}")
        return
    if not specs:
        print(
            f"[插件] 已扫描 {root_label}（仅首层 {PLUGIN_FILE_PREFIX}*.py），"
            "未发现可用插件"
        )
        return
    print(
        f"[插件] 已扫描 {root_label}（仅首层 {PLUGIN_FILE_PREFIX}*.py），"
        f"发现 {len(specs)} 个:"
    )
    for p in specs:
        print(f"  - {p.id}  {p.title}")


def _build_registry() -> tuple[PluginSpec, ...]:
    root = _plugins_dir()
    specs = _load_plugins_from_dir()
    _print_discovered_plugins(specs, root=root)
    return tuple(specs)


_ALL: tuple[PluginSpec, ...] = _build_registry()
REGISTRY: Dict[str, PluginSpec] = {p.id: p for p in _ALL}


def list_plugin_specs() -> List[PluginSpec]:
    """返回所有已发现的插件定义（供 API 与前端展示）。"""
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
