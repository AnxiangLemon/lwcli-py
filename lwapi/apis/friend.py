# lwapi/apis/friend.py
"""微信好友与通讯录：参数由 SDK 组装为 JSON，调用方无需手写 body。"""

from __future__ import annotations

from typing import Any, Optional

from ..models.friend_requests import (
    FriendBlacklistParam,
    FriendDeleteParam,
    FriendGetContactDetailParam,
    FriendGetContactListParam,
    FriendPassVerifyParam,
    FriendSearchParam,
    FriendSendRequestParam,
    FriendSetRemarksParam,
)
from ..transport import AsyncHTTPTransport


class FriendClient:
    """好友业务 HTTP 封装。"""

    def __init__(self, transport: AsyncHTTPTransport) -> None:
        self._t = transport

    async def blacklist(
        self, to_wxid: str, val: int, *, timeout: Optional[float] = None
    ) -> Any:
        """添加或移除黑名单（15 添加，7 移除）。"""
        return await self._t.post(
            "/Friend/Blacklist",
            json=FriendBlacklistParam(to_wxid=to_wxid, val=val).to_api(),
            timeout=timeout,
        )

    async def delete_friend(self, to_wxid: str, *, timeout: Optional[float] = None) -> Any:
        """删除指定好友。"""
        return await self._t.post(
            "/Friend/Delete",
            json=FriendDeleteParam(to_wxid=to_wxid).to_api(),
            timeout=timeout,
        )

    async def get_contact_detail(
        self,
        towxids: str,
        chat_room: Optional[str] = None,
        *,
        timeout: Optional[float] = None,
    ) -> Any:
        """获取联系人详情（towxids 为逗号分隔 wxid，最多 20 个）。"""
        return await self._t.post(
            "/Friend/GetContactDetail",
            json=FriendGetContactDetailParam(towxids=towxids, chat_room=chat_room).to_api(),
            timeout=timeout,
        )

    async def get_contact_list(
        self,
        current_wx_contact_seq: int = 0,
        current_chat_room_contact_seq: int = 0,
        *,
        timeout: Optional[float] = None,
    ) -> Any:
        """分页获取通讯录好友与群列表。"""
        return await self._t.post(
            "/Friend/GetContactList",
            json=FriendGetContactListParam(
                current_wx_contact_seq=current_wx_contact_seq,
                current_chat_room_contact_seq=current_chat_room_contact_seq,
            ).to_api(),
            timeout=timeout,
        )

    async def pass_verify(
        self, v1: str, v2: str, scene: int, *, timeout: Optional[float] = None
    ) -> Any:
        """同意好友验证请求。"""
        return await self._t.post(
            "/Friend/PassVerify",
            json=FriendPassVerifyParam(v1=v1, v2=v2, scene=scene).to_api(),
            timeout=timeout,
        )

    async def search(
        self,
        to_user_name: str,
        from_scene: int = 0,
        search_scene: int = 1,
        *,
        timeout: Optional[float] = None,
    ) -> Any:
        """搜索联系人。"""
        return await self._t.post(
            "/Friend/Search",
            json=FriendSearchParam(
                to_user_name=to_user_name,
                from_scene=from_scene,
                search_scene=search_scene,
            ).to_api(),
            timeout=timeout,
        )

    async def send_request(
        self,
        v1: str,
        v2: str,
        scene: int,
        verify_content: str = "",
        *,
        timeout: Optional[float] = None,
    ) -> Any:
        """发送好友添加请求。"""
        return await self._t.post(
            "/Friend/SendRequest",
            json=FriendSendRequestParam(
                v1=v1, v2=v2, scene=scene, verify_content=verify_content
            ).to_api(),
            timeout=timeout,
        )

    async def set_remarks(
        self, to_wxid: str, remarks: str, *, timeout: Optional[float] = None
    ) -> Any:
        """设置好友备注。"""
        return await self._t.post(
            "/Friend/SetRemarks",
            json=FriendSetRemarksParam(to_wxid=to_wxid, remarks=remarks).to_api(),
            timeout=timeout,
        )
