"""
消息插件子包：链式处理、注册表、配置与内置实现。

对外给业务侧的稳定入口见 src.message_handler 中的 default_message_handler。
"""

from src.plugins.chain import composite_message_handler

__all__ = ["composite_message_handler"]
