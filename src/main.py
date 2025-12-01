# src/main.py
import asyncio
from .bot_manager import start_all_bots
from .utils import setup_logger

async def main():
    setup_logger("main")
    try:
        await start_all_bots()
    except KeyboardInterrupt:
        print("\n\n用户主动退出，拜拜")

if __name__ == "__main__":
    asyncio.run(main())