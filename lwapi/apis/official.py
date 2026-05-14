# lwapi/apis/official.py
"""微信公众号：参数由 SDK 组装。"""

from __future__ import annotations

from typing import Any, Optional

from ..models.official_requests import (
    OfficialBizProfileV2Param,
    OfficialDefaultParam,
    OfficialGetkeyParam,
    OfficialReadParam,
)
from ..transport import AsyncHTTPTransport


class OfficialClient:
    def __init__(self, transport: AsyncHTTPTransport) -> None:
        self._t = transport

    async def biz_profile_v2(
        self,
        biz_user_name: str,
        page_size: int = 10,
        scene: int = 1,
        *,
        timeout: Optional[float] = None,
    ) -> Any:
        """拉取公众号历史文章列表。"""
        return await self._t.post(
            "/Official/BizProfileV2",
            json=OfficialBizProfileV2Param(
                biz_user_name=biz_user_name, page_size=page_size, scene=scene
            ).to_api(),
            timeout=timeout,
        )

    async def follow(self, appid: str, *, timeout: Optional[float] = None) -> Any:
        """关注公众号。"""
        return await self._t.post(
            "/Official/Follow", json=OfficialDefaultParam(appid=appid).to_api(), timeout=timeout
        )

    async def get_app_msg_ext(self, url: str, *, timeout: Optional[float] = None) -> Any:
        """阅读文章（模拟打开文章）。"""
        return await self._t.post(
            "/Official/GetAppMsgExt", json=OfficialReadParam(url=url).to_api(), timeout=timeout
        )

    async def get_app_msg_ext_like(self, url: str, *, timeout: Optional[float] = None) -> Any:
        """点赞文章。"""
        return await self._t.post(
            "/Official/GetAppMsgExtLike",
            json=OfficialReadParam(url=url).to_api(),
            timeout=timeout,
        )

    async def get_comment_data(self, url: str, *, timeout: Optional[float] = None) -> Any:
        """获取文章评论数据。"""
        return await self._t.post(
            "/Official/GetCommentData",
            json=OfficialReadParam(url=url).to_api(),
            timeout=timeout,
        )

    async def get_read_data(self, url: str, *, timeout: Optional[float] = None) -> Any:
        """获取文章阅读统计。"""
        return await self._t.post(
            "/Official/GetReadData", json=OfficialReadParam(url=url).to_api(), timeout=timeout
        )

    async def jsapi_pre_verify(
        self, appid: str, url: str, *, timeout: Optional[float] = None
    ) -> Any:
        """JSAPI 预验证 / 签名。"""
        return await self._t.post(
            "/Official/JSAPIPreVerify",
            json=OfficialGetkeyParam(appid=appid, url=url).to_api(),
            timeout=timeout,
        )

    async def mp_get_a8key(self, url: str, *, timeout: Optional[float] = None) -> Any:
        """获取文章 A8Key。"""
        return await self._t.post(
            "/Official/MpGetA8Key", json=OfficialReadParam(url=url).to_api(), timeout=timeout
        )

    async def oauth_authorize(
        self, appid: str, url: str, *, timeout: Optional[float] = None
    ) -> Any:
        """OAuth 授权页信息。"""
        return await self._t.post(
            "/Official/OauthAuthorize",
            json=OfficialGetkeyParam(appid=appid, url=url).to_api(),
            timeout=timeout,
        )

    async def quit(self, appid: str, *, timeout: Optional[float] = None) -> Any:
        """取消关注公众号。"""
        return await self._t.post(
            "/Official/Quit", json=OfficialDefaultParam(appid=appid).to_api(), timeout=timeout
        )
