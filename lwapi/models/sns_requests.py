# lwapi/models/sns_requests.py
"""朋友圈（MmSns / sns.*）请求体。"""

from __future__ import annotations

from typing import Optional

from pydantic import Field

from .json_payload import ApiJsonBody


class SnsCommentParam(ApiJsonBody):
    id: str = Field(..., description="朋友圈内容 ID")
    op_type: int = Field(
        ...,
        serialization_alias="type",
        description="1 点赞 2 文本评论 3 消息评论 4 with 5 陌生人点赞",
    )
    content: str = Field("", description="评论正文，type 2/3 时有效")
    reply_commnet_id: int = Field(0, serialization_alias="replyCommnetId", description="回复的评论 ID")


class SnsGetDetailParam(ApiJsonBody):
    towxid: str = Field(..., description="目标用户 wxid")
    maxid: int = Field(0, description="最大朋友圈 ID，首次 0")
    fristpagemd5: str = Field("", description="首页 MD5，首次留空")


class SnsGetIdDetailParam(ApiJsonBody):
    towxid: str = Field(..., description="发布者 wxid")
    id: int = Field(..., description="朋友圈内容 ID")


class SnsGetListParam(ApiJsonBody):
    maxid: int = Field(0, description="最大朋友圈 ID，首次 0")
    fristpagemd5: str = Field("", description="首页 MD5，首次留空")


class SnsPostParam(ApiJsonBody):
    content: str = Field(..., description="朋友圈 XML 内容")
    black_list: str = Field("", serialization_alias="blackList", description="黑名单 wxid，逗号分隔")
    with_user_list: str = Field("", serialization_alias="withUserList", description="可见用户 wxid，逗号分隔")


class SnsSyncParam(ApiJsonBody):
    synckey: Optional[str] = Field(None, description="同步密钥，首次可空")


class SnsOperationParam(ApiJsonBody):
    id: str = Field(..., description="朋友圈内容 ID")
    op_type: int = Field(
        ...,
        serialization_alias="type",
        description="1 删动态 2 隐私 3 公开 4 删评论 5 取消赞",
    )
    commnet_id: int = Field(0, serialization_alias="commnetId", description="评论 ID，type=4 时有效")


class SnsPrivacySettingsParam(ApiJsonBody):
    feature_code: int = Field(
        ...,
        serialization_alias="function",
        description="功能代码（具体值见服务端说明）",
    )
    value: int = Field(..., description="设置值")


class SnsUploadParam(ApiJsonBody):
    image_b64: str = Field(..., serialization_alias="base64", description="图片或视频 Base64")
