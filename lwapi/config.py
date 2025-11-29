from typing import Optional

class Config:
    def __init__(
        self,
        base_url: str,
        default_wxid: Optional[str] = None,
        timeout: int = 10,
        retries: int = 2,
    ):
        self.base_url = base_url.rstrip("/")
        self.default_wxid = default_wxid
        self.timeout = timeout
        self.retries = retries
