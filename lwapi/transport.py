# lwapi/transport.py
import httpx
from loguru import logger
from typing import TypeVar, Type, Optional

from .config import ClientConfig
from .models.base import ApiResponse
from .exceptions import HttpError, ApiError

_T = TypeVar("_T")

class AsyncHTTPTransport:
    def __init__(self, config: ClientConfig):
        self._config = config
        self._client = httpx.AsyncClient(timeout=config.timeout)

    async def post(self, path: str, 
                   json: Optional[dict] = None,
                   params: Optional[dict] = None,
                   *,
                   response_model: Type[_T] = dict  # 默认返回 dict，避免每次都写
                   ) -> _T:
        """
        完全兼容 Python 3.9+ 的泛型 post
        - 自动加 X-Wxid
        - 自动检查 HTTP 200 + 业务 code 200
        - 直接返回你指定的模型实例（类型提示完美）
        """
        headers = {}
        if self._config.x_wxid:
            headers["X-Wxid"] = self._config.x_wxid

        url = self._config.api_url(path)

        try:
            response = await self._client.post(url, json=json, params=params, headers=headers)
        except httpx.TimeoutException:
            raise HttpError(0, "request timeout")
        except httpx.NetworkError as e:
            raise HttpError(0, f"network error: {e}")

        if response.status_code != 200:
            logger.error(f"HTTP {response.status_code} {url} {response.text[:300]}")
            raise HttpError(response.status_code, response.text[:500])

        try:
            raw_json = response.json()
        except ValueError as e:
            raise HttpError(response.status_code, f"invalid json: {e}")

        # 解析外层通用结构
        try:
            api_resp = ApiResponse[response_model].model_validate(raw_json)
        except Exception as e:
            logger.error(f"ApiResponse parse failed: {raw_json}")
            raise ApiError(-1, f"response format error: {e}")

        if api_resp.code != 200:
            logger.error(f"API error [{api_resp.code}] {path}: {api_resp.message}")
            raise ApiError(api_resp.code, api_resp.message or "unknown error")

        return api_resp.data  # 类型自动推断为 _T，完美！