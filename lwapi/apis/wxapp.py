# lwapi/apis/wxapp.py
"""微信小程序 WxApp：参数由 SDK 组装。"""

from __future__ import annotations

from typing import Any, Optional

from ..models.wxapp_requests import (
    WxAppDefaultParam,
    WxAppJsOperateParam,
    WxAppSearchSuggestionParam,
    WxAppWebSearchParam,
)
from ..transport import AsyncHTTPTransport


class WxAppClient:
    def __init__(self, transport: AsyncHTTPTransport) -> None:
        self._t = transport

    async def js_login(self, appid: str, *, timeout: Optional[float] = None) -> Any:
        """小程序 JS 登录授权。"""
        return await self._t.post(
            "/WxApp/JSLogin", json=WxAppDefaultParam(appid=appid).to_api(), timeout=timeout
        )

    async def js_operate_wx_data(
        self, appid: str, data: str, opt: int, *, timeout: Optional[float] = None
    ) -> Any:
        """小程序数据操作。"""
        return await self._t.post(
            "/WxApp/JSOperateWxData",
            json=WxAppJsOperateParam(appid=appid, data=data, opt=opt).to_api(),
            timeout=timeout,
        )

    async def search_suggestion(self, keys: str, *, timeout: Optional[float] = None) -> Any:
        """搜索建议。"""
        return await self._t.post(
            "/WxApp/SearchSuggestion",
            json=WxAppSearchSuggestionParam(keys=keys).to_api(),
            timeout=timeout,
        )

    async def web_search(
        self,
        keys: str,
        off_set: int = 0,
        suggestion_id: str = "",
        *,
        timeout: Optional[float] = None,
    ) -> Any:
        """小程序内网页搜索。"""
        return await self._t.post(
            "/WxApp/WebSearch",
            json=WxAppWebSearchParam(
                keys=keys, off_set=off_set, suggestion_id=suggestion_id
            ).to_api(),
            timeout=timeout,
        )
