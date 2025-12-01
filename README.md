# lwcli-py

一个简单的4.0微信机器人框架

```t
lwapi-py/
├── config/
│   └── accounts.json                  # 你原来的配置文件
├── logs/
│   └── bot_*.log                      # 自动生成，按日期/大小轮转
├── src/
│   ├── __init__.py
│   ├── main.py                        # 入口，几乎只有几行
│   ├── bot_manager.py                 # 全局机器人管理器 + 启动/停止
│   ├── account_loader.py              # 安全读写 accounts.json
│   ├── qr_printer.py                  # 美化二维码打印（支持终端 + 保存图片）
│   ├── message_handler.py             # 所有消息逻辑，干净易扩展
│   ├── login_service.py               # 封装二次登录、二维码登录、心跳
│   └── utils.py                       # 通用工具（日志、常量、原子写文件等）
├── requirements.txt
└── run.py                             # 一键启动脚本（软链接或快捷方式）
```
