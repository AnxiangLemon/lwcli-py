# lwapi/models/official_requests.py
"""公众号相关请求体（对齐 swagger official.*）。"""

from __future__ import annotations

from pydantic import Field

from .json_payload import ApiJsonBody


class OfficialBizProfileV2Param(ApiJsonBody):
    biz_user_name: str = Field(..., serialization_alias="bizUserName", description="公众号 biz 用户名")
    page_size: int = Field(10, serialization_alias="pageSize", description="每页条数")
    scene: int = Field(1, description="来源场景")


class OfficialDefaultParam(ApiJsonBody):
    appid: str = Field(..., description="公众号 AppID")


class OfficialReadParam(ApiJsonBody):
    url: str = Field(..., description="公众号文章链接")


class OfficialGetkeyParam(ApiJsonBody):
    appid: str = Field(..., description="公众号 AppID")
    url: str = Field(..., description="网页或授权页 URL")
