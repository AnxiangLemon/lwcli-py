"""
LwApi 消息回调的统一入口（历史名称 default_message_handler）。

BotService 仍从此处 import；实际逻辑在 plugins.chain 中按配置串联多个插件。
"""

from src.plugins.chain import composite_message_handler as default_message_handler

__all__ = ["default_message_handler"]
