"""
插件设置面板的静态文件解析（防路径穿越）。
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from aiohttp import web

from src.plugins.registry import REGISTRY


def panel_url_for(plugin_id: str) -> Optional[str]:
    spec = REGISTRY.get(plugin_id)
    if spec is None or spec.settings_panel_dir is None:
        return None
    return f"/plugin-ui/{plugin_id}/"


def resolve_panel_file(plugin_id: str, rel_path: str) -> Optional[Path]:
    spec = REGISTRY.get(plugin_id)
    if spec is None or spec.settings_panel_dir is None:
        return None
    root = spec.settings_panel_dir.resolve()
    rel = (rel_path or "").strip().lstrip("/") or "index.html"
    target = (root / rel).resolve()
    try:
        target.relative_to(root)
    except ValueError:
        return None
    if target.is_dir():
        target = (target / "index.html").resolve()
        try:
            target.relative_to(root)
        except ValueError:
            return None
    if not target.is_file():
        return None
    return target


async def serve_plugin_panel(request: web.Request) -> web.StreamResponse:
    plugin_id = request.match_info["plugin_id"]
    rel = request.match_info.get("path") or ""
    path = resolve_panel_file(plugin_id, rel)
    if path is None:
        raise web.HTTPNotFound()
    return web.FileResponse(path, headers={"Cache-Control": "no-cache"})


async def serve_plugin_panel_index(request: web.Request) -> web.StreamResponse:
    plugin_id = request.match_info["plugin_id"]
    path = resolve_panel_file(plugin_id, "index.html")
    if path is None:
        raise web.HTTPNotFound()
    return web.FileResponse(path, headers={"Cache-Control": "no-cache"})
