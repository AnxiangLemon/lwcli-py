"""
项目启动脚本：进入 Web 运维台入口 src.main.main()。

KeyboardInterrupt 时静默退出；其它未捕获异常打印一行提示（便于 systemd / 终端观察）。
"""

from src.main import main

try:
    main()
except KeyboardInterrupt:
    print("\n程序已完全退出，所有资源已释放")
except Exception as e:
    print(f"程序异常崩溃: {e}")
