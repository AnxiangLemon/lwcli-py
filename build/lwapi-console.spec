# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec：在目标系统上执行对应 build-*. 脚本生成 dist/

import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

ROOT = Path(SPECPATH).resolve().parent.parent
ENTRY = ROOT / "build" / "entry.py"
STATIC = ROOT / "src" / "web" / "static"

block_cipher = None

datas = [
    (str(STATIC), "src/web/static"),
]

hiddenimports = collect_submodules("lwapi") + collect_submodules("pydantic") + [
    "aiohttp",
    "aiohttp.web",
    "httpx",
    "httpx._transports",
    "loguru",
    "dotenv",
    "PIL",
    "PIL.Image",
    "qrcode",
    "qrcode.image.pil",
    "multidict",
    "yarl",
    "frozenlist",
    "aiosignal",
    "async_timeout",
    "charset_normalizer",
]

a = Analysis(
    [str(ENTRY)],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="lwapi-console",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="lwapi-console",
)

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="lwapi-console.app",
        icon=None,
        bundle_identifier="com.lwapi.console",
    )
