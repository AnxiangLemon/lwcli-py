# run.py
from src.main import main
import asyncio

try:
    asyncio.run(main())
except KeyboardInterrupt:
    # 优雅静默退出
    print("\n程序已完全退出，所有资源已释放")
except Exception as e:
    # 防止意外崩溃
    print(f"程序异常崩溃: {e}")