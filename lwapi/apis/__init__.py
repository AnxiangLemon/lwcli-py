"""
按领域聚合 API 客户端导出，便于外部按需引用。

业务实现与 ``login.py`` / ``msg.py`` 一样位于 ``lwapi/apis/`` 根目录下各模块。
"""

from .favor import FavorClient
from .finder import FinderClient
from .friend import FriendClient
from .group import GroupClient
from .label import LabelClient
from .login import LoginClient, LoginError, QRStatus
from .mmsns import MmSnsClient
from .msg import MsgClient
from .official import OfficialClient
from .other import OtherClient
from .user import UserClient
from .wxapp import WxAppClient

__all__ = [
    "LoginClient",
    "LoginError",
    "QRStatus",
    "MsgClient",
    "FavorClient",
    "FinderClient",
    "FriendClient",
    "GroupClient",
    "LabelClient",
    "MmSnsClient",
    "OfficialClient",
    "OtherClient",
    "UserClient",
    "WxAppClient",
]
