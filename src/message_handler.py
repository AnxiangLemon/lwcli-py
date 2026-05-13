# src/message_handler.py
"""LwApi 消息入口（兼容旧 import 名 default_message_handler）。

业务逻辑请放到 src/plugins/ 下的内置或自研插件，并在运维台「插件管理」中启用。
"""

from src.plugins.chain import composite_message_handler as default_message_handler

__all__ = ["default_message_handler"]
