# lwapi/models/label_requests.py
"""标签相关请求体（对齐 swagger label.*）。"""

from __future__ import annotations

from pydantic import Field

from .json_payload import ApiJsonBody


class LabelAddParam(ApiJsonBody):
    label_name: str = Field(..., serialization_alias="labelName", description="新标签名称")


class LabelDeleteParam(ApiJsonBody):
    label_id: str = Field(..., serialization_alias="labelId", description="标签 ID")


class LabelUpdateListParam(ApiJsonBody):
    label_id: str = Field(..., serialization_alias="labelId", description="标签 ID")
    to_wxids: str = Field(..., serialization_alias="toWxids", description="成员 wxid 列表，逗号分隔")


class LabelUpdateNameParam(ApiJsonBody):
    label_id: int = Field(..., serialization_alias="labelId", description="标签 ID")
    new_name: str = Field(..., serialization_alias="newName", description="新名称")
