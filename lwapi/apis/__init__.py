"""
按领域聚合 API 客户端导出，便于外部按需引用。
"""

from .login import LoginClient, LoginError, QRStatus
from .msg import MsgClient

__all__ = [
    "LoginClient",
    "LoginError",
    "QRStatus",
    "MsgClient",
]
