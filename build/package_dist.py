#!/usr/bin/env python3
"""
将 PyInstaller 产物与 config/plugins 模板合并，并生成 zip 发布包。

由各平台 build-*. 脚本在打包成功后调用；也可单独运行：
  python build/package_dist.py
"""

from __future__ import annotations

import platform
import shutil
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = Path(__file__).resolve().parent / "dist-template"
DIST = ROOT / "dist"
APP_NAME = "lwapi-console"
VERSION = "0.1.0"


def _read_version() -> str:
    pyproject = ROOT / "pyproject.toml"
    if not pyproject.is_file():
        return VERSION
    for line in pyproject.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("version") and "=" in line:
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return VERSION


def artifact_paths() -> tuple[Path, Path]:
    """
    返回 (可执行文件或 .app 路径, 可写数据目录)。

    Windows/Linux onedir：二者均为 dist/lwapi-console/
    macOS：lwapi-console.app + 与 .app 同级的 dist/ 目录
    """
    system = sys.platform
    if system == "darwin":
        app = DIST / f"{APP_NAME}.app"
        if not app.is_dir():
            raise FileNotFoundError(f"未找到 {app}，请先运行 build-macos.sh")
        return app, app.parent

    folder = DIST / APP_NAME
    if system == "win32":
        exe = folder / f"{APP_NAME}.exe"
    else:
        exe = folder / APP_NAME
    if not exe.is_file():
        raise FileNotFoundError(f"未找到 {exe}，请先运行对应平台的 build 脚本")
    return exe, folder


def _copy_if_missing(src: Path, dest: Path) -> None:
    if dest.exists():
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    if src.is_dir():
        shutil.copytree(src, dest)
    else:
        shutil.copy2(src, dest)


def _ensure_default_config(data_root: Path) -> None:
    config_dir = data_root / "config"
    config_dir.mkdir(parents=True, exist_ok=True)

    accounts = config_dir / "accounts.json"
    if not accounts.exists():
        accounts.write_text("[]\n", encoding="utf-8")

    plugins = config_dir / "plugins.json"
    template_plugins = TEMPLATE / "config" / "plugins.json"
    if not plugins.exists() and template_plugins.is_file():
        shutil.copy2(template_plugins, plugins)


def _sync_plugins(data_root: Path) -> None:
    dest = data_root / "plugins"
    dest.mkdir(parents=True, exist_ok=True)
    src = ROOT / "plugins"
    if src.is_dir():
        for item in src.iterdir():
            target = dest / item.name
            if target.exists():
                continue
            if item.is_dir():
                shutil.copytree(item, target)
            else:
                shutil.copy2(item, target)
    readme = TEMPLATE / "plugins" / "README.txt"
    if readme.is_file() and not any(dest.iterdir()):
        shutil.copy2(readme, dest / "README.txt")


def _copy_template_files(data_root: Path) -> None:
    for name in (".env.example", "使用说明.txt"):
        src = TEMPLATE / name
        if src.is_file():
            _copy_if_missing(src, data_root / name)
    logs = data_root / "logs"
    logs.mkdir(parents=True, exist_ok=True)


def _platform_tag() -> str:
    mapping = {
        "win32": "windows",
        "darwin": "macos",
        "linux": "linux",
    }
    name = mapping.get(sys.platform, sys.platform)
    machine = platform.machine().lower()
    return f"{name}-{machine}"


def make_zip(data_root: Path, version: str) -> Path:
    tag = _platform_tag()
    zip_path = DIST / f"{APP_NAME}-{version}-{tag}.zip"
    if zip_path.exists():
        zip_path.unlink()

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        if sys.platform == "darwin":
            app = data_root / f"{APP_NAME}.app"
            for path in app.rglob("*"):
                if path.is_file():
                    arc = path.relative_to(data_root)
                    zf.write(path, arc.as_posix())
        else:
            folder = data_root / APP_NAME
            for path in folder.rglob("*"):
                if path.is_file():
                    arc = path.relative_to(data_root)
                    zf.write(path, arc.as_posix())

        for extra in (".env.example", "使用说明.txt"):
            p = data_root / extra
            if p.is_file():
                zf.write(p, extra)

        for sub in ("config", "plugins", "logs"):
            base = data_root / sub
            if not base.exists():
                continue
            for path in base.rglob("*"):
                if path.is_file():
                    arc = path.relative_to(data_root)
                    zf.write(path, arc.as_posix())

    return zip_path


def main() -> int:
    version = _read_version()
    artifact, data_root = artifact_paths()
    print(f"产物: {artifact}")
    print(f"数据目录: {data_root}")

    _ensure_default_config(data_root)
    _sync_plugins(data_root)
    _copy_template_files(data_root)

    zip_path = make_zip(data_root, version)
    print(f"已生成发布包: {zip_path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except FileNotFoundError as e:
        print(f"错误: {e}", file=sys.stderr)
        raise SystemExit(1) from e
