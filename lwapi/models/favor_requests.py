# lwapi/models/favor_requests.py
"""收藏相关请求体（对齐 swagger favor.*）。"""

from __future__ import annotations

from typing import Optional

from pydantic import Field

from .json_payload import ApiJsonBody


class FavorDelParam(ApiJsonBody):
    fav_id: int = Field(..., serialization_alias="favId", description="收藏项 ID")


class FavorGetFavItemParam(ApiJsonBody):
    fav_id: int = Field(..., serialization_alias="favId", description="收藏项 ID")


class FavorSyncParam(ApiJsonBody):
    key_buf: Optional[str] = Field(
        None,
        serialization_alias="keyBuf",
        description="上次同步返回的密钥，首次可空",
    )
