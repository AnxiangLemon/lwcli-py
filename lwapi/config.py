# config.py
from dataclasses import dataclass
from typing import Optional

@dataclass
class ClientConfig:
    base_url: str                   # 基础 URL
    timeout: float = 15.0           # 请求超时
    x_wxid: Optional[str] = None    # 登录后 wxid（动态更新）

    def api_url(self, path: str) -> str:
        """根据接口路径和基础 URL 拼接出完整的 API URL"""
        return f"{self.base_url.rstrip('/')}/api/{path.lstrip('/')}"

    def set_wxid(self, wxid: str):
        """登录后更新 wxid"""
        self.x_wxid = wxid
