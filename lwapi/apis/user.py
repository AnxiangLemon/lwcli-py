# lwapi/apis/user.py
"""用户资料与二维码：参数由 SDK 组装。"""

from __future__ import annotations

from typing import Any, Optional

from ..models.user_requests import (
    UserGetQRCodeParam,
    UserGetUserAuthListParam,
    UserWxaAppIdParam,
)
from ..transport import AsyncHTTPTransport


class UserClient:
    def __init__(self, transport: AsyncHTTPTransport) -> None:
        self._t = transport

    async def get_contact_profile(self, *, timeout: Optional[float] = None) -> Any:
        """获取当前账号联系人资料摘要。"""
        return await self._t.post("/User/GetContactProfile", json=None, timeout=timeout)

    async def get_qrcode(self, style: int = 8, *, timeout: Optional[float] = None) -> Any:
        """获取个人二维码。"""
        return await self._t.post(
            "/User/GetQRCode", json=UserGetQRCodeParam(style=style).to_api(), timeout=timeout
        )

    async def get_user_auth_list(
        self,
        key_word: str = "",
        next_page_data: int = 0,
        *,
        timeout: Optional[float] = None,
    ) -> Any:
        """获取已授权应用列表。"""
        return await self._t.post(
            "/User/GetUserAuthList",
            json=UserGetUserAuthListParam(
                key_word=key_word, next_page_data=next_page_data
            ).to_api(),
            timeout=timeout,
        )

    async def query_app(self, appid: str, *, timeout: Optional[float] = None) -> Any:
        """搜索已授权 APP。"""
        return await self._t.post(
            "/User/QueryApp", json=UserWxaAppIdParam(appid=appid).to_api(), timeout=timeout
        )

    async def subscribe_msg(self, appid: str, *, timeout: Optional[float] = None) -> Any:
        """小程序订阅消息授权信息。"""
        return await self._t.post(
            "/User/SubscribeMsg", json=UserWxaAppIdParam(appid=appid).to_api(), timeout=timeout
        )

    async def wxa_app_get_auth_info(self, appid: str, *, timeout: Optional[float] = None) -> Any:
        """获取小程序授权信息。"""
        return await self._t.post(
            "/User/WxaAppGetAuthInfo",
            json=UserWxaAppIdParam(appid=appid).to_api(),
            timeout=timeout,
        )
