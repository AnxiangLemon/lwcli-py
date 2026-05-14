# lwapi/models/group_requests.py
"""群聊相关请求体（对齐 swagger group.*）。"""

from __future__ import annotations

from pydantic import Field

from .json_payload import ApiJsonBody


class GroupAddChatRoomParam(ApiJsonBody):
    chat_room_name: str = Field(..., serialization_alias="chatRoomName", description="群聊 ID")
    to_wxids: str = Field(..., serialization_alias="toWxids", description="成员 wxid 列表，逗号分隔")


class GroupConsentToJoinParam(ApiJsonBody):
    url: str = Field(..., description="群邀请链接，从消息 XML 获取")


class GroupCreateChatRoomParam(ApiJsonBody):
    to_wxids: str = Field(..., serialization_alias="toWxids", description="初始成员 wxid，逗号分隔，至少三人")


class GroupFacingCreateChatRoomParam(ApiJsonBody):
    password: str = Field(..., description="面对面密码")
    op_code: int = Field(..., serialization_alias="opCode", description="操作码")
    latitude: float = Field(..., description="纬度")
    longitude: float = Field(..., description="经度")


class GroupGetChatRoomParam(ApiJsonBody):
    gid: str = Field(..., description="群聊 ID，多个用逗号分隔")


class GroupMoveContactListParam(ApiJsonBody):
    gid: str = Field(..., description="群聊 ID")
    val: int = Field(..., description="3 保存到通讯录，2 移除")


class GroupOperateChatRoomAdminParam(ApiJsonBody):
    gid: str = Field(..., description="群聊 ID")
    to_wxids: str = Field(..., serialization_alias="toWxids", description="管理员相关 wxid 列表，逗号分隔")
    val: int = Field(..., description="1 添加管理员，2 删除管理员，3 转让群主")


class GroupOperateChatRoomInfoParam(ApiJsonBody):
    gid: str = Field(..., description="群聊 ID")
    content: str = Field(..., description="群名称或公告内容")


class GroupQuitGroupParam(ApiJsonBody):
    gid: str = Field(..., description="要退出的群聊 ID")


class GroupScanIntoGroupParam(ApiJsonBody):
    url: str = Field(..., description="群二维码链接")
