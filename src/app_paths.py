"""
安装根目录与静态资源路径（开发目录 / PyInstaller 冻结包）。

冻结运行时：
- 可写数据（config、plugins、logs、.env）位于「程序旁」目录；
- macOS .app 为 .app 所在文件夹（与 .app 同级），避免写入 Bundle 内部。
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def _macos_app_bundle_root(exe: Path) -> Path | None:
    p = exe
    for _ in range(12):
        if p.name.endswith(".app"):
            return p.parent
        if p.parent == p:
            break
        p = p.parent
    return None


def install_root() -> Path:
    """可写数据根目录（config/、plugins/、logs/、.env）。"""
    if is_frozen():
        exe = Path(sys.executable).resolve()
        if sys.platform == "darwin":
            bundle_parent = _macos_app_bundle_root(exe)
            if bundle_parent is not None:
                return bundle_parent
        return exe.parent
    return Path(__file__).resolve().parent.parent


def prepare_runtime() -> Path:
    """将工作目录切到 install_root，并确保常用目录存在。"""
    root = install_root()
    os.chdir(root)
    for name in ("config", "plugins", "logs"):
        (root / name).mkdir(parents=True, exist_ok=True)
    return root


def static_dir() -> Path:
    """Web 静态资源目录（冻结时从 _MEIPASS 读取）。"""
    if is_frozen():
        return Path(sys._MEIPASS) / "src" / "web" / "static"
    return Path(__file__).resolve().parent / "web" / "static"


def env_file() -> Path:
    return install_root() / ".env"
