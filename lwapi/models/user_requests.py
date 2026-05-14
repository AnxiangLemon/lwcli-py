# lwapi/models/user_requests.py
"""用户资料相关请求体（对齐 swagger user.*）。"""

from __future__ import annotations

from pydantic import Field

from .json_payload import ApiJsonBody


class UserGetQRCodeParam(ApiJsonBody):
    style: int = Field(8, description="二维码样式，8 为默认")


class UserGetUserAuthListParam(ApiJsonBody):
    key_word: str = Field("", serialization_alias="keyWord", description="搜索关键字")
    next_page_data: int = Field(0, serialization_alias="nextPageData", description="0 或 1 分页")


class UserWxaAppIdParam(ApiJsonBody):
    appid: str = Field(..., description="小程序或应用 AppID")
