# src/main.py
import os
from aiohttp import web
from .utils import setup_logger
from .web.app import create_app

def main() -> None:
    setup_logger("main")
    host = os.getenv("LWAPI_WEB_HOST", "0.0.0.0")
    port = int(os.getenv("LWAPI_WEB_PORT", "8090"))
    print(f"Web 控制台已启动: http://localhost:{port}")
    web.run_app(create_app(), host=host, port=port)

if __name__ == "__main__":
    main()