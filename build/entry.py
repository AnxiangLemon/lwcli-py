"""
PyInstaller 入口：修正工作目录、加载 .env、默认打开浏览器后启动运维台。
"""

from __future__ import annotations

import os
import sys

# zoneinfo on Windows / PyInstaller needs IANA tz database (plugins may use ZoneInfo)
try:
    import tzdata  # noqa: F401
except ImportError:
    pass

from src.app_paths import prepare_runtime

prepare_runtime()

if getattr(sys, "frozen", False) and not os.environ.get("LWAPI_OPEN_BROWSER"):
    os.environ["LWAPI_OPEN_BROWSER"] = "1"

from src.main import main

try:
    main()
except KeyboardInterrupt:
    print("\n程序已完全退出，所有资源已释放")
except Exception as e:
    print(f"程序异常崩溃: {e}")
    raise SystemExit(1) from e
