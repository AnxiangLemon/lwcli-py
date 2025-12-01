# src/login_service.py
from lwapi.models.login import ProxyInfo
from loguru import logger
from .qr_printer import print_qr_terminal
from .utils import logger as root_logger

class LoginService:
    def __init__(self, client, device_id: str, proxy=None, remark: str = ""):
        self.client = client
        self.device_id = device_id
        self.proxy = ProxyInfo(**proxy) if proxy else None
        self.remark = remark

    async def login(self, saved_wxid: str = "") -> str:
        login = self.client.login

        # 1. 尝试二次登录
        if saved_wxid:
            self.client.transport._config.set_wxid(saved_wxid)
            if await login.sec_auto_login():
                root_logger.success(f"【{self.remark}】二次登录成功 → {saved_wxid}")
                return saved_wxid

        # 2. 二维码登录
        root_logger.info(f"【{self.remark}】正在获取二维码...")
        qr = await login.get_qr_code(self.device_id, self.proxy)

        url = f"http://weixin.qq.com/x/{qr.uuid}"
        print_qr_terminal(url)

        root_logger.info(f"【{self.remark}】请用微信扫码 → {url}")
        wxid = await login.check_qr_code(qr.uuid, timeout=300)

        root_logger.success(f"【{self.remark}】登录成功！wxid = {wxid}")
        return wxid