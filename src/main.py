"""
进程入口：启动 aiohttp Web 运维台（账号、插件、日志与扫码事件）。

环境变量 LWAPI_WEB_HOST / LWAPI_WEB_PORT 控制监听地址与端口；
底层 LWAPI HTTP 基址由 BotService 使用的 LWAPI_BASE_URL 决定（见 .env）。
"""

from __future__ import annotations

import os

from aiohttp import web

from .utils import setup_logger
from .web.app import create_app


def main() -> None:
    setup_logger("main")
    host = os.getenv("LWAPI_WEB_HOST", "0.0.0.0")
    port = int(os.getenv("LWAPI_WEB_PORT", "8090"))
    display_host = "127.0.0.1" if host in ("0.0.0.0", "::") else host
    print(f"Web 运维台已启动: http://{display_host}:{port}")
    web.run_app(create_app(), host=host, port=port)


if __name__ == "__main__":
    main()
