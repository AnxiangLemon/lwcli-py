# lwapi/transport.py
import httpx
from .config import ClientConfig
from .models.base import ResponseResult
from .exceptions import HttpError, ApiError
from typing import Optional

class SyncHTTPTransport:
    def __init__(self, config: ClientConfig):
        """初始化 HTTP 客户端，使用给定的配置"""
        self._client = httpx.Client(timeout=config.timeout, verify=config.verify_ssl)
        self._config = config

    def post(self, path: str, json: dict = None, x_wxid: Optional[str] = None) -> ResponseResult:
        """发送 POST 请求，动态添加 wxid 请求头"""
        headers = {}

        # 只在 wxid 已设置的情况下加入 X-Wxid 请求头
        if self._config.x_wxid:
            headers["X-Wxid"] = self._config.x_wxid
        
        url = self._config.api_url(path)

        response = self._client.post(url, json=json, headers=headers)

        if response.status_code != 200:
            raise HttpError(response.status_code, response.text)

        data = response.json()
        result = ResponseResult.model_validate(data)
        
        if result.RetCode  != 200:
            raise ApiError(result.RetCode , result.message)
        
        return result
