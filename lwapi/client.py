# lwapi/client.py
from .config import ClientConfig
from .transport import AsyncHTTPTransport
from .apis.login import LoginClient
from .apis.msg import MsgClient

class LwApiClient:
    def __init__(self, base_url: str, timeout: float = 10.0):
        """初始化 SDK 客户端"""
        self.config = ClientConfig(base_url=base_url, timeout=timeout)
        self.transport = AsyncHTTPTransport(config=self.config)
        self.login = LoginClient(self.transport)
        self.msg = MsgClient(self.transport)
        
        # 【关键注入】让 MsgClient 知道自己的“主人”是谁
        self.msg.client = self   # ← 加上这行就完事了！
        # 用于控制整个客户端生命周期
        self._closed = False

    # ==================== 支持 async with ====================
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.aclose()  # 异步关闭

    async def aclose(self):
        """异步关闭客户端（推荐主动调用）"""
        if self._closed:
            return
        self._closed = True

        # 停止心跳（如果正在运行）
        if hasattr(self.login, "stop_heartbeat"):
            self.login.stop_heartbeat()

        # 关闭底层 HTTP 连接池
        if hasattr(self.transport, "_client") and self.transport._client:
            await self.transport._client.aclose()
