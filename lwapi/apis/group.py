# lwapi/apis/group.py
"""微信群聊：参数由 SDK 组装。"""

from __future__ import annotations

from typing import Any, Optional

from ..models.group_requests import (
    GroupAddChatRoomParam,
    GroupConsentToJoinParam,
    GroupCreateChatRoomParam,
    GroupFacingCreateChatRoomParam,
    GroupGetChatRoomParam,
    GroupMoveContactListParam,
    GroupOperateChatRoomAdminParam,
    GroupOperateChatRoomInfoParam,
    GroupQuitGroupParam,
    GroupScanIntoGroupParam,
)
from ..transport import AsyncHTTPTransport


class GroupClient:
    def __init__(self, transport: AsyncHTTPTransport) -> None:
        self._t = transport

    async def add_chat_room_member(
        self, chat_room_name: str, to_wxids: str, *, timeout: Optional[float] = None
    ) -> Any:
        """向群内添加成员（40 人以内群）。"""
        return await self._t.post(
            "/Group/AddChatRoomMember",
            json=GroupAddChatRoomParam(
                chat_room_name=chat_room_name, to_wxids=to_wxids
            ).to_api(),
            timeout=timeout,
        )

    async def consent_to_join(self, url: str, *, timeout: Optional[float] = None) -> Any:
        """通过邀请链接同意入群。"""
        return await self._t.post(
            "/Group/ConsentToJoin",
            json=GroupConsentToJoinParam(url=url).to_api(),
            timeout=timeout,
        )

    async def create_chat_room(self, to_wxids: str, *, timeout: Optional[float] = None) -> Any:
        """创建群聊（初始成员 wxid 逗号分隔，至少三人）。"""
        return await self._t.post(
            "/Group/CreateChatRoom",
            json=GroupCreateChatRoomParam(to_wxids=to_wxids).to_api(),
            timeout=timeout,
        )

    async def del_chat_room_member(
        self, chat_room_name: str, to_wxids: str, *, timeout: Optional[float] = None
    ) -> Any:
        """移除群成员。"""
        return await self._t.post(
            "/Group/DelChatRoomMember",
            json=GroupAddChatRoomParam(
                chat_room_name=chat_room_name, to_wxids=to_wxids
            ).to_api(),
            timeout=timeout,
        )

    async def facing_create_chat_room(
        self,
        password: str,
        op_code: int,
        latitude: float,
        longitude: float,
        *,
        timeout: Optional[float] = None,
    ) -> Any:
        """面对面建群。"""
        return await self._t.post(
            "/Group/FacingCreateChatRoom",
            json=GroupFacingCreateChatRoomParam(
                password=password,
                op_code=op_code,
                latitude=latitude,
                longitude=longitude,
            ).to_api(),
            timeout=timeout,
        )

    async def get_chat_room_info(self, gid: str, *, timeout: Optional[float] = None) -> Any:
        """获取群基本信息（不含公告）。"""
        return await self._t.post(
            "/Group/GetChatRoomInfo",
            json=GroupGetChatRoomParam(gid=gid).to_api(),
            timeout=timeout,
        )

    async def get_chat_room_info_detail(
        self, gid: str, *, timeout: Optional[float] = None
    ) -> Any:
        """获取群详细信息（含公告）。"""
        return await self._t.post(
            "/Group/GetChatRoomInfoDetail",
            json=GroupGetChatRoomParam(gid=gid).to_api(),
            timeout=timeout,
        )

    async def get_chat_room_member_detail(
        self, gid: str, *, timeout: Optional[float] = None
    ) -> Any:
        """获取群成员详情。"""
        return await self._t.post(
            "/Group/GetChatRoomMemberDetail",
            json=GroupGetChatRoomParam(gid=gid).to_api(),
            timeout=timeout,
        )

    async def get_qrcode(self, gid: str, *, timeout: Optional[float] = None) -> Any:
        """获取群二维码。"""
        return await self._t.post(
            "/Group/GetQRCode", json=GroupGetChatRoomParam(gid=gid).to_api(), timeout=timeout
        )

    async def invite_chat_room_member(
        self, chat_room_name: str, to_wxids: str, *, timeout: Optional[float] = None
    ) -> Any:
        """邀请成员（40 人以上群）。"""
        return await self._t.post(
            "/Group/InviteChatRoomMember",
            json=GroupAddChatRoomParam(
                chat_room_name=chat_room_name, to_wxids=to_wxids
            ).to_api(),
            timeout=timeout,
        )

    async def move_contact_list(
        self, gid: str, val: int, *, timeout: Optional[float] = None
    ) -> Any:
        """将群保存到通讯录或移除（3 添加 2 移除）。"""
        return await self._t.post(
            "/Group/MoveContactList",
            json=GroupMoveContactListParam(gid=gid, val=val).to_api(),
            timeout=timeout,
        )

    async def operate_chat_room_admin(
        self, gid: str, to_wxids: str, val: int, *, timeout: Optional[float] = None
    ) -> Any:
        """添加/删除管理员或转让群主。"""
        return await self._t.post(
            "/Group/OperateChatRoomAdmin",
            json=GroupOperateChatRoomAdminParam(
                gid=gid, to_wxids=to_wxids, val=val
            ).to_api(),
            timeout=timeout,
        )

    async def quit(self, gid: str, *, timeout: Optional[float] = None) -> Any:
        """退出群聊。"""
        return await self._t.post(
            "/Group/Quit", json=GroupQuitGroupParam(gid=gid).to_api(), timeout=timeout
        )

    async def scan_into_group(self, url: str, *, timeout: Optional[float] = None) -> Any:
        """扫码通过链接入群。"""
        return await self._t.post(
            "/Group/ScanIntoGroup",
            json=GroupScanIntoGroupParam(url=url).to_api(),
            timeout=timeout,
        )

    async def scan_into_group_enterprise(
        self, url: str, *, timeout: Optional[float] = None
    ) -> Any:
        """扫码加入企业群。"""
        return await self._t.post(
            "/Group/ScanIntoGroupEnterprise",
            json=GroupScanIntoGroupParam(url=url).to_api(),
            timeout=timeout,
        )

    async def set_chat_room_announcement(
        self, gid: str, content: str, *, timeout: Optional[float] = None
    ) -> Any:
        """设置群公告。"""
        return await self._t.post(
            "/Group/SetChatRoomAnnouncement",
            json=GroupOperateChatRoomInfoParam(gid=gid, content=content).to_api(),
            timeout=timeout,
        )

    async def set_chat_room_name(
        self, gid: str, content: str, *, timeout: Optional[float] = None
    ) -> Any:
        """修改群名称。"""
        return await self._t.post(
            "/Group/SetChatRoomName",
            json=GroupOperateChatRoomInfoParam(gid=gid, content=content).to_api(),
            timeout=timeout,
        )

    async def set_chat_room_remarks(
        self, gid: str, content: str, *, timeout: Optional[float] = None
    ) -> Any:
        """设置群备注。"""
        return await self._t.post(
            "/Group/SetChatRoomRemarks",
            json=GroupOperateChatRoomInfoParam(gid=gid, content=content).to_api(),
            timeout=timeout,
        )
