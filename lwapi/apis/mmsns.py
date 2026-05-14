# lwapi/apis/mmsns.py
"""朋友圈（MmSns）：参数由 SDK 组装。"""

from __future__ import annotations

from typing import Any, Optional

from ..models.sns_requests import (
    SnsCommentParam,
    SnsGetDetailParam,
    SnsGetIdDetailParam,
    SnsGetListParam,
    SnsOperationParam,
    SnsPostParam,
    SnsPrivacySettingsParam,
    SnsSyncParam,
    SnsUploadParam,
)
from ..transport import AsyncHTTPTransport


class MmSnsClient:
    def __init__(self, transport: AsyncHTTPTransport) -> None:
        self._t = transport

    async def comment(
        self,
        sns_id: str,
        op_type: int,
        content: str = "",
        reply_commnet_id: int = 0,
        *,
        timeout: Optional[float] = None,
    ) -> Any:
        """点赞或评论朋友圈。"""
        return await self._t.post(
            "/MmSns/Comment",
            json=SnsCommentParam(
                id=sns_id,
                op_type=op_type,
                content=content,
                reply_commnet_id=reply_commnet_id,
            ).to_api(),
            timeout=timeout,
        )

    async def get_detail(
        self,
        towxid: str,
        maxid: int = 0,
        fristpagemd5: str = "",
        *,
        timeout: Optional[float] = None,
    ) -> Any:
        """获取指定用户朋友圈列表页。"""
        return await self._t.post(
            "/MmSns/GetDetail",
            json=SnsGetDetailParam(
                towxid=towxid, maxid=maxid, fristpagemd5=fristpagemd5
            ).to_api(),
            timeout=timeout,
        )

    async def get_id_detail(
        self, towxid: str, sns_id: int, *, timeout: Optional[float] = None
    ) -> Any:
        """获取单条朋友圈详情。"""
        return await self._t.post(
            "/MmSns/GetIdDetail",
            json=SnsGetIdDetailParam(towxid=towxid, id=sns_id).to_api(),
            timeout=timeout,
        )

    async def get_list(
        self, maxid: int = 0, fristpagemd5: str = "", *, timeout: Optional[float] = None
    ) -> Any:
        """获取自己朋友圈首页列表。"""
        return await self._t.post(
            "/MmSns/GetList",
            json=SnsGetListParam(maxid=maxid, fristpagemd5=fristpagemd5).to_api(),
            timeout=timeout,
        )

    async def post(
        self,
        content: str,
        black_list: str = "",
        with_user_list: str = "",
        *,
        timeout: Optional[float] = None,
    ) -> Any:
        """发布朋友圈（content 为 XML）。"""
        return await self._t.post(
            "/MmSns/MmSnsPost",
            json=SnsPostParam(
                content=content,
                black_list=black_list,
                with_user_list=with_user_list,
            ).to_api(),
            timeout=timeout,
        )

    async def sync(
        self, synckey: Optional[str] = None, *, timeout: Optional[float] = None
    ) -> Any:
        """同步朋友圈。"""
        return await self._t.post(
            "/MmSns/MmSnsSync", json=SnsSyncParam(synckey=synckey).to_api(), timeout=timeout
        )

    async def operation(
        self,
        sns_id: str,
        op_type: int,
        commnet_id: int = 0,
        *,
        timeout: Optional[float] = None,
    ) -> Any:
        """删除 / 隐私 / 删评论等操作。"""
        return await self._t.post(
            "/MmSns/Operation",
            json=SnsOperationParam(id=sns_id, op_type=op_type, commnet_id=commnet_id).to_api(),
            timeout=timeout,
        )

    async def privacy_settings(
        self, feature_code: int, value: int, *, timeout: Optional[float] = None
    ) -> Any:
        """朋友圈权限设置。"""
        return await self._t.post(
            "/MmSns/PrivacySettings",
            json=SnsPrivacySettingsParam(feature_code=feature_code, value=value).to_api(),
            timeout=timeout,
        )

    async def upload(self, image_b64: str, *, timeout: Optional[float] = None) -> Any:
        """上传朋友圈图片/视频素材（Base64）。"""
        return await self._t.post(
            "/MmSns/Upload", json=SnsUploadParam(image_b64=image_b64).to_api(), timeout=timeout
        )
