# client.py
from .config import ClientConfig
from .transport import SyncHTTPTransport
from .apis.login import LoginClient

class LwApiClient:
    def __init__(self, base_url: str, timeout: float = 10.0):
        """初始化 SDK 客户端"""
        self.config = ClientConfig(base_url=base_url, timeout=timeout)
        self.transport = SyncHTTPTransport(config=self.config)
        
        # 初始化各个子客户端
        self.login = LoginClient(self.transport)

    def login(self, username: str, password: str) -> bool:
        """调用登录接口，登录成功后更新 wxid"""
        return self.login.login(username, password)
