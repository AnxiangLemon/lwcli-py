"""
进程入口：启动 aiohttp Web 运维台（账号、插件、日志与扫码事件）。

环境变量 LWAPI_WEB_HOST / LWAPI_WEB_PORT 控制监听地址与端口；
底层 LWAPI HTTP 基址由 BotService 使用的 LWAPI_BASE_URL 决定（见 .env）。
"""
from __future__ import annotations

import os
import threading
import webbrowser
from typing import Optional

from aiohttp import web

from .app_paths import prepare_runtime
from .utils import setup_logger
from .web.app import create_app

prepare_runtime()

# 日志初始化（全局复用）
logger = setup_logger("main")

# 环境变量默认值常量（便于统一维护）
DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 26121
ENV_HOST_KEY = "LWAPI_WEB_HOST"
ENV_PORT_KEY = "LWAPI_WEB_PORT"


def get_server_config() -> tuple[str, int]:
    """
    从环境变量读取 Web 服务配置，提供类型安全与异常处理
    Returns:
        (host: str, port: int)
    """
    # 读取主机地址
    host: str = os.getenv(ENV_HOST_KEY, DEFAULT_HOST)

    # 读取并安全转换端口（处理非数字异常）
    port_str: Optional[str] = os.getenv(ENV_PORT_KEY)
    try:
        port: int = int(port_str) if port_str is not None else DEFAULT_PORT
    except ValueError:
        logger.warning(f"环境变量 {ENV_PORT_KEY} 值非法，使用默认端口 {DEFAULT_PORT}")
        port = DEFAULT_PORT

    return host, port


def get_display_host(host: str) -> str:
    """将 0.0.0.0/:: 转换为本地访问地址，提升用户体验"""
    return "127.0.0.1" if host in ("0.0.0.0", "::") else host


def _should_open_browser() -> bool:
    return os.getenv("LWAPI_OPEN_BROWSER", "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def _schedule_open_browser(display_host: str, port: int) -> None:
    url = f"http://{display_host}:{port}"

    def _open() -> None:
        try:
            webbrowser.open(url, new=1)
        except Exception as e:
            logger.warning(f"自动打开浏览器失败: {e}")

    threading.Timer(1.2, _open).start()


def main() -> None:
    """Web 运维台主启动函数"""
    host, port = get_server_config()
    display_host = get_display_host(host)

    # 使用日志替代 print（更规范，支持日志级别/持久化）
    logger.info(f"Web 运维台启动成功 → http://{display_host}:{port}")
    logger.info(f"监听地址: {host}:{port}")

    if _should_open_browser():
        _schedule_open_browser(display_host, port)

    # 启动 aiohttp 应用
    web.run_app(create_app(), host=host, port=port)


if __name__ == "__main__":
    main()