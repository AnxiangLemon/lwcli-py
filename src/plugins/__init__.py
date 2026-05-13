"""消息插件：在 src/plugins/ 下注册内置插件，由 config/plugins.json 控制启用列表。"""

from src.plugins.chain import composite_message_handler

__all__ = ["composite_message_handler"]
