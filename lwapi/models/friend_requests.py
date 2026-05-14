# lwapi/models/friend_requests.py
"""好友 / 通讯录相关请求体（对齐 swagger friend.*）。"""

from __future__ import annotations

from typing import Optional

from pydantic import Field

from .json_payload import ApiJsonBody


class FriendBlacklistParam(ApiJsonBody):
    to_wxid: str = Field(..., serialization_alias="toWxid", description="目标用户 wxid")
    val: int = Field(..., description="15 添加黑名单，7 移除黑名单")


class FriendDeleteParam(ApiJsonBody):
    to_wxid: str = Field(..., serialization_alias="toWxid", description="要删除的好友 wxid")


class FriendGetContactDetailParam(ApiJsonBody):
    towxids: str = Field(..., serialization_alias="towxids", description="目标 wxid 列表，逗号分隔，最多 20 个")
    chat_room: Optional[str] = Field(None, serialization_alias="chatRoom", description="群聊场景可填，单聊可空")


class FriendGetContactListParam(ApiJsonBody):
    current_wx_contact_seq: int = Field(
        0,
        serialization_alias="currentWxcontactSeq",
        description="当前联系人序列号，首次填 0",
    )
    current_chat_room_contact_seq: int = Field(
        0,
        serialization_alias="currentChatRoomContactSeq",
        description="当前群聊联系人序列号，首次填 0",
    )


class FriendPassVerifyParam(ApiJsonBody):
    v1: str = Field(..., description="申请者 V1")
    v2: str = Field(..., description="申请者 V2")
    scene: int = Field(..., description="来源场景，从请求消息 XML 获取")


class FriendSearchParam(ApiJsonBody):
    to_user_name: str = Field(..., serialization_alias="toUserName", description="目标 wxid 或用户名")
    from_scene: int = Field(0, serialization_alias="fromScene", description="来源场景，默认 0")
    search_scene: int = Field(1, serialization_alias="searchScene", description="搜索场景，默认 1")


class FriendSendRequestParam(ApiJsonBody):
    v1: str = Field(..., description="目标用户 V1")
    v2: str = Field(..., description="目标用户 V2")
    scene: int = Field(..., description="来源场景")
    verify_content: str = Field("", serialization_alias="verifyContent", description="验证消息")


class FriendSetRemarksParam(ApiJsonBody):
    to_wxid: str = Field(..., serialization_alias="toWxid", description="目标好友 wxid")
    remarks: str = Field(..., description="备注名称")
