# lwapi/models/wxapp_requests.py
"""小程序 WxApp 请求体。"""

from __future__ import annotations

from pydantic import Field

from .json_payload import ApiJsonBody


class WxAppDefaultParam(ApiJsonBody):
    appid: str = Field(..., description="小程序 AppID")


class WxAppJsOperateParam(ApiJsonBody):
    appid: str = Field(..., description="小程序 AppID")
    data: str = Field(..., description="操作数据")
    opt: int = Field(..., description="操作类型")


class WxAppSearchSuggestionParam(ApiJsonBody):
    keys: str = Field(..., description="搜索关键字")


class WxAppWebSearchParam(ApiJsonBody):
    keys: str = Field(..., description="搜索关键字")
    off_set: int = Field(0, serialization_alias="offSet", description="分页偏移")
    suggestion_id: str = Field("", serialization_alias="suggestionId", description="建议 ID")
