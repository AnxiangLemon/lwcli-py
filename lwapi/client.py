# lwapi/client.py
from .config import ClientConfig
from .transport import AsyncHTTPTransport
from .apis.favor import FavorClient
from .apis.finder import FinderClient
from .apis.friend import FriendClient
from .apis.group import GroupClient
from .apis.label import LabelClient
from .apis.login import LoginClient
from .apis.mmsns import MmSnsClient
from .apis.msg import MsgClient
from .apis.official import OfficialClient
from .apis.other import OtherClient
from .apis.user import UserClient
from .apis.wxapp import WxAppClient


class LwApiClient:
    """
    LwApi 异步 SDK。

    - ``login``：扫码登录、心跳、长连接等（LoginClient）。
    - ``msg``：消息长轮询与各类发送接口（参数由 SDK 组装 JSON）。
    - ``favor`` / ``friend`` / ``group`` 等：其它业务域的同类封装。
    """

    def __init__(self, base_url: str, timeout: float = 30.0):
        """初始化 SDK 客户端。timeout 为普通接口默认超时；消息 Sync 等在各自调用处单独放宽。"""
        self.config = ClientConfig(base_url=base_url, timeout=timeout)
        self.transport = AsyncHTTPTransport(config=self.config)
        
        t = self.transport
        self.login = LoginClient(t)
        self.msg = MsgClient(t)

        self.favor = FavorClient(t)
        self.finder = FinderClient(t)
        self.friend = FriendClient(t)
        self.group = GroupClient(t)
        self.label = LabelClient(t)
        self.mmsns = MmSnsClient(t)
        self.official = OfficialClient(t)
        self.other = OtherClient(t)
        self.user = UserClient(t)
        self.wxapp = WxAppClient(t)

        # 反向注入 client，便于消息回调里拿到完整 SDK 能力。
        self.msg.client = self
        # 用于控制整个客户端生命周期，防止重复关闭。
        self._closed = False

    # ==================== 支持 async with ====================
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.aclose()

    async def aclose(self):
        """异步关闭客户端（推荐主动调用）"""
        if self._closed:
            return
        self._closed = True

        # 停止消息轮询，避免后台任务持有旧连接。
        if hasattr(self.msg, "stop"):
            self.msg.stop()
        if hasattr(self.msg, "wait_stop"):
            await self.msg.wait_stop()

        # 停止心跳、缓存刷新等后台任务并等待结束，避免关闭连接池后仍有请求。
        if hasattr(self.login, "join_background_tasks"):
            await self.login.join_background_tasks()
        elif hasattr(self.login, "stop_heartbeat"):
            self.login.stop_heartbeat()

        # 统一通过 transport 的关闭方法释放底层连接池。
        await self.transport.aclose()

    def set_wxid(self, wxid: str) -> None:
        """设置当前会话 wxid（用于请求头 X-Wxid）。"""
        self.config.set_wxid(wxid)

    @property
    def wxid(self) -> str:
        """获取当前会话 wxid，未登录时返回空字符串。"""
        return self.config.x_wxid or ""
