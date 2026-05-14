# lwapi/apis/generated.py
"""
由 scripts/generate_lwapi_from_swagger.py 根据 swagger.json 自动生成，请勿手改。
重新生成: python scripts/generate_lwapi_from_swagger.py

本模块为「薄封装」：统一走 AsyncHTTPTransport.post，已自动附带 X-Wxid 请求头（请先 LwApiClient.set_wxid）。
默认不挂载到 LwApiClient；业务代码请用 apis.login.LoginClient、apis.msg.MsgClient 等。
若尚未提供领域封装，可 ``from lwapi.apis.generated import GeneratedApis`` 并传入 ``transport`` 使用。
"""

from __future__ import annotations

from typing import Any, Optional

from ..transport import AsyncHTTPTransport


class FavorApi:
    """本组接口与 Swagger 中对应 Tag 一致，各方法含中文说明。"""

    def __init__(self, transport: AsyncHTTPTransport) -> None:
        self._t = transport

    async def favor_del(self, body: dict[str, Any], *, timeout: Optional[float] = None) -> Any:
        """
        删除收藏
        
        删除指定的微信收藏项
        
        路径: 见本函数内 self._t.post 的第一个参数（与 swagger paths 一致）。
        鉴权: 依赖客户端已设置 wxid（请求头 X-Wxid 由传输层自动附加）。
        
        请求体 JSON:
          删除参数：FavId为收藏项ID（从同步收藏接口获取）
        
        Returns:
          transport 解包后的 data（通常为 dict）。
        """
        return await self._t.post('/Favor/Del', json=body, params=None, timeout=timeout)

    async def favor_get_fav_info(self, *, timeout: Optional[float] = None) -> Any:
        """
        获取收藏信息
        
        获取用户的微信收藏信息，包括收藏列表或元数据
        
        路径: 见本函数内 self._t.post 的第一个参数（与 swagger paths 一致）。
        鉴权: 依赖客户端已设置 wxid（请求头 X-Wxid 由传输层自动附加）。
        
        Returns:
          transport 解包后的 data（通常为 dict）。
        """
        return await self._t.post('/Favor/GetFavInfo', json=None, params=None, timeout=timeout)

    async def favor_get_fav_item(self, body: dict[str, Any], *, timeout: Optional[float] = None) -> Any:
        """
        读取收藏内容
        
        读取指定收藏项的详细内容
        
        路径: 见本函数内 self._t.post 的第一个参数（与 swagger paths 一致）。
        鉴权: 依赖客户端已设置 wxid（请求头 X-Wxid 由传输层自动附加）。
        
        请求体 JSON:
          收藏项参数：FavId为收藏项ID（从同步收藏接口获取）
        
        Returns:
          transport 解包后的 data（通常为 dict）。
        """
        return await self._t.post('/Favor/GetFavItem', json=body, params=None, timeout=timeout)

    async def favor_sync(self, body: dict[str, Any], *, timeout: Optional[float] = None) -> Any:
        """
        同步收藏
        
        同步用户的微信收藏数据，返回收藏项列表和同步密钥
        
        路径: 见本函数内 self._t.post 的第一个参数（与 swagger paths 一致）。
        鉴权: 依赖客户端已设置 wxid（请求头 X-Wxid 由传输层自动附加）。
        
        请求体 JSON:
          同步参数：KeyBuf为上次同步返回的密钥（首次同步可留空）
        
        Returns:
          transport 解包后的 data（通常为 dict）。
        """
        return await self._t.post('/Favor/Sync', json=body, params=None, timeout=timeout)


class FinderApi:
    """本组接口与 Swagger 中对应 Tag 一致，各方法含中文说明。"""

    def __init__(self, transport: AsyncHTTPTransport) -> None:
        self._t = transport

    async def finder_user_prepare(self, wxid: str, *, timeout: Optional[float] = None) -> Any:
        """
        用户中心
        
        路径: 见本函数内 self._t.post 的第一个参数（与 swagger paths 一致）。
        鉴权: 依赖客户端已设置 wxid（请求头 X-Wxid 由传输层自动附加）。
        
        Query 参数:
          - wxid（wxid，必填） — 请输登录后的wxid
        
        Returns:
          transport 解包后的 data（通常为 dict）。
        """
        params: dict[str, Any] = {}
        params["wxid"] = wxid
        return await self._t.post('/Finder/UserPrepare', json=None, params=params, timeout=timeout)


class FriendApi:
    """本组接口与 Swagger 中对应 Tag 一致，各方法含中文说明。"""

    def __init__(self, transport: AsyncHTTPTransport) -> None:
        self._t = transport

    async def friend_blacklist(self, body: dict[str, Any], *, timeout: Optional[float] = None) -> Any:
        """
        添加或移除黑名单
        
        将指定用户添加或移除微信黑名单
        
        路径: 见本函数内 self._t.post 的第一个参数（与 swagger paths 一致）。
        鉴权: 依赖客户端已设置 wxid（请求头 X-Wxid 由传输层自动附加）。
        
        请求体 JSON:
          黑名单参数：ToWxid为目标用户微信ID，Val为操作值（15添加，7移除）
        
        Returns:
          transport 解包后的 data（通常为 dict）。
        """
        return await self._t.post('/Friend/Blacklist', json=body, params=None, timeout=timeout)

    async def friend_delete(self, body: dict[str, Any], *, timeout: Optional[float] = None) -> Any:
        """
        删除好友
        
        删除指定的微信好友
        
        路径: 见本函数内 self._t.post 的第一个参数（与 swagger paths 一致）。
        鉴权: 依赖客户端已设置 wxid（请求头 X-Wxid 由传输层自动附加）。
        
        请求体 JSON:
          删除参数：ToWxid为要删除的好友微信ID
        
        Returns:
          transport 解包后的 data（通常为 dict）。
        """
        return await self._t.post('/Friend/Delete', json=body, params=None, timeout=timeout)

    async def friend_get_contact_detail(self, body: dict[str, Any], *, timeout: Optional[float] = None) -> Any:
        """
        获取通讯录好友详情
        
        获取指定微信联系人（最多20个）的详细信息，群聊留空
        
        路径: 见本函数内 self._t.post 的第一个参数（与 swagger paths 一致）。
        鉴权: 依赖客户端已设置 wxid（请求头 X-Wxid 由传输层自动附加）。
        
        请求体 JSON:
          详情参数：UserNameList为目标用户微信ID列表（逗号分隔，最多20个）
        
        Returns:
          transport 解包后的 data（通常为 dict）。
        """
        return await self._t.post('/Friend/GetContactDetail', json=body, params=None, timeout=timeout)

    async def friend_get_contact_list(self, body: dict[str, Any], *, timeout: Optional[float] = None) -> Any:
        """
        获取通讯录好友列表
        
        获取微信通讯录中的好友和群聊列表
        
        路径: 见本函数内 self._t.post 的第一个参数（与 swagger paths 一致）。
        鉴权: 依赖客户端已设置 wxid（请求头 X-Wxid 由传输层自动附加）。
        
        请求体 JSON:
          列表参数：CurrentWxcontactSeq和CurrentChatRoomContactSeq为序列号（首次请求填0）
        
        Returns:
          transport 解包后的 data（通常为 dict）。
        """
        return await self._t.post('/Friend/GetContactList', json=body, params=None, timeout=timeout)

    async def friend_pass_verify(self, body: dict[str, Any], *, timeout: Optional[float] = None) -> Any:
        """
        同意好友验证
        
        通过收到的微信好友请求
        
        路径: 见本函数内 self._t.post 的第一个参数（与 swagger paths 一致）。
        鉴权: 依赖客户端已设置 wxid（请求头 X-Wxid 由传输层自动附加）。
        
        请求体 JSON:
          验证参数：V1和V2为申请者的标识，Scene为来源场景（从请求消息的XML获取）
        
        Returns:
          transport 解包后的 data（通常为 dict）。
        """
        return await self._t.post('/Friend/PassVerify', json=body, params=None, timeout=timeout)

    async def friend_search(self, body: dict[str, Any], *, timeout: Optional[float] = None) -> Any:
        """
        搜索联系人
        
        搜索微信联系人，支持通过微信ID或用户名查找
        
        路径: 见本函数内 self._t.post 的第一个参数（与 swagger paths 一致）。
        鉴权: 依赖客户端已设置 wxid（请求头 X-Wxid 由传输层自动附加）。
        
        请求体 JSON:
          搜索参数：ToUserName为目标用户微信ID或用户名，FromScene为来源场景（默认0），SearchScene为搜索场景（默认1，爆粉情况下需特殊通道）
        
        Returns:
          transport 解包后的 data（通常为 dict）。
        """
        return await self._t.post('/Friend/Search', json=body, params=None, timeout=timeout)

    async def friend_send_request(self, body: dict[str, Any], *, timeout: Optional[float] = None) -> Any:
        """
        发送好友请求
        
        向指定用户发送微信好友请求
        
        路径: 见本函数内 self._t.post 的第一个参数（与 swagger paths 一致）。
        鉴权: 依赖客户端已设置 wxid（请求头 X-Wxid 由传输层自动附加）。
        
        请求体 JSON:
          请求参数：V1和V2为目标用户的标识（必填），Scene为来源场景，VerifyContent为验证消息
        
        Returns:
          transport 解包后的 data（通常为 dict）。
        """
        return await self._t.post('/Friend/SendRequest', json=body, params=None, timeout=timeout)

    async def friend_set_remarks(self, body: dict[str, Any], *, timeout: Optional[float] = None) -> Any:
        """
        设置好友备注
        
        为指定微信好友设置备注名称
        
        路径: 见本函数内 self._t.post 的第一个参数（与 swagger paths 一致）。
        鉴权: 依赖客户端已设置 wxid（请求头 X-Wxid 由传输层自动附加）。
        
        请求体 JSON:
          备注参数：ToWxid为目标好友微信ID，Remarks为备注名称
        
        Returns:
          transport 解包后的 data（通常为 dict）。
        """
        return await self._t.post('/Friend/SetRemarks', json=body, params=None, timeout=timeout)


class GroupApi:
    """本组接口与 Swagger 中对应 Tag 一致，各方法含中文说明。"""

    def __init__(self, transport: AsyncHTTPTransport) -> None:
        self._t = transport

    async def group_add_chat_room_member(self, body: dict[str, Any], *, timeout: Optional[float] = None) -> Any:
        """
        添加群成员
        
        向微信群聊添加成员（适用于40人以内群聊）
        
        路径: 见本函数内 self._t.post 的第一个参数（与 swagger paths 一致）。
        鉴权: 依赖客户端已设置 wxid（请求头 X-Wxid 由传输层自动附加）。
        
        请求体 JSON:
          添加参数：ToWxids为目标用户微信ID列表（逗号分隔），ChatRoomName为群聊ID
        
        Returns:
          transport 解包后的 data（通常为 dict）。
        """
        return await self._t.post('/Group/AddChatRoomMember', json=body, params=None, timeout=timeout)

    async def group_consent_to_join(self, body: dict[str, Any], *, timeout: Optional[float] = None) -> Any:
        """
        同意加入群聊
        
        通过群聊邀请链接同意加入微信群聊
        
        路径: 见本函数内 self._t.post 的第一个参数（与 swagger paths 一致）。
        鉴权: 依赖客户端已设置 wxid（请求头 X-Wxid 由传输层自动附加）。
        
        请求体 JSON:
          加入参数：Url为群聊邀请链接（从消息XML获取）
        
        Returns:
          transport 解包后的 data（通常为 dict）。
        """
        return await self._t.post('/Group/ConsentToJoin', json=body, params=None, timeout=timeout)

    async def group_create_chat_room(self, body: dict[str, Any], *, timeout: Optional[float] = None) -> Any:
        """
        创建群聊
        
        创建新的微信群聊，需指定初始成员
        
        路径: 见本函数内 self._t.post 的第一个参数（与 swagger paths 一致）。
        鉴权: 依赖客户端已设置 wxid（请求头 X-Wxid 由传输层自动附加）。
        
        请求体 JSON:
          创建参数：ToWxids为初始群成员微信ID列表（逗号分隔，至少三个）
        
        Returns:
          transport 解包后的 data（通常为 dict）。
        """
        return await self._t.post('/Group/CreateChatRoom', json=body, params=None, timeout=timeout)

    async def group_del_chat_room_member(self, body: dict[str, Any], *, timeout: Optional[float] = None) -> Any:
        """
        删除群成员
        
        从微信群聊中删除指定成员
        
        路径: 见本函数内 self._t.post 的第一个参数（与 swagger paths 一致）。
        鉴权: 依赖客户端已设置 wxid（请求头 X-Wxid 由传输层自动附加）。
        
        请求体 JSON:
          删除参数：ToWxids为目标用户微信ID列表（逗号分隔），ChatRoomName为群聊ID
        
        Returns:
          transport 解包后的 data（通常为 dict）。
        """
        return await self._t.post('/Group/DelChatRoomMember', json=body, params=None, timeout=timeout)

    async def group_facing_create_chat_room(self, body: dict[str, Any], *, timeout: Optional[float] = None) -> Any:
        """
        面对面创建群聊
        
        通过密码和地理位置面对面创建微信群聊
        
        路径: 见本函数内 self._t.post 的第一个参数（与 swagger paths 一致）。
        鉴权: 依赖客户端已设置 wxid（请求头 X-Wxid 由传输层自动附加）。
        
        请求体 JSON:
          创建参数：Password为群聊密码，OpCode为操作码，Latitude为纬度，Longitude为经度
        
        Returns:
          transport 解包后的 data（通常为 dict）。
        """
        return await self._t.post('/Group/FacingCreateChatRoom', json=body, params=None, timeout=timeout)

    async def group_get_chat_room_info(self, body: dict[str, Any], *, timeout: Optional[float] = None) -> Any:
        """
        获取群聊信息
        
        获取指定微信群聊的基本信息（不含公告）
        
        路径: 见本函数内 self._t.post 的第一个参数（与 swagger paths 一致）。
        鉴权: 依赖客户端已设置 wxid（请求头 X-Wxid 由传输层自动附加）。
        
        请求体 JSON:
          查询参数：Gid为群聊ID（多个ID用逗号分隔）
        
        Returns:
          transport 解包后的 data（通常为 dict）。
        """
        return await self._t.post('/Group/GetChatRoomInfo', json=body, params=None, timeout=timeout)

    async def group_get_chat_room_info_detail(self, body: dict[str, Any], *, timeout: Optional[float] = None) -> Any:
        """
        获取群聊详细信息
        
        获取指定微信群聊的详细信息（包含公告）
        
        路径: 见本函数内 self._t.post 的第一个参数（与 swagger paths 一致）。
        鉴权: 依赖客户端已设置 wxid（请求头 X-Wxid 由传输层自动附加）。
        
        请求体 JSON:
          查询参数：Gid为群聊ID
        
        Returns:
          transport 解包后的 data（通常为 dict）。
        """
        return await self._t.post('/Group/GetChatRoomInfoDetail', json=body, params=None, timeout=timeout)

    async def group_get_chat_room_member_detail(self, body: dict[str, Any], *, timeout: Optional[float] = None) -> Any:
        """
        获取群成员详情
        
        获取指定微信群聊的成员详细信息
        
        路径: 见本函数内 self._t.post 的第一个参数（与 swagger paths 一致）。
        鉴权: 依赖客户端已设置 wxid（请求头 X-Wxid 由传输层自动附加）。
        
        请求体 JSON:
          查询参数：Gid为群聊ID
        
        Returns:
          transport 解包后的 data（通常为 dict）。
        """
        return await self._t.post('/Group/GetChatRoomMemberDetail', json=body, params=None, timeout=timeout)

    async def group_get_qrcode(self, body: dict[str, Any], *, timeout: Optional[float] = None) -> Any:
        """
        获取群聊二维码
        
        获取指定微信群聊的二维码
        
        路径: 见本函数内 self._t.post 的第一个参数（与 swagger paths 一致）。
        鉴权: 依赖客户端已设置 wxid（请求头 X-Wxid 由传输层自动附加）。
        
        请求体 JSON:
          查询参数：Gid为群聊ID
        
        Returns:
          transport 解包后的 data（通常为 dict）。
        """
        return await self._t.post('/Group/GetQRCode', json=body, params=None, timeout=timeout)

    async def group_invite_chat_room_member(self, body: dict[str, Any], *, timeout: Optional[float] = None) -> Any:
        """
        邀请群成员
        
        邀请成员加入微信群聊（适用于40人以上群聊）
        
        路径: 见本函数内 self._t.post 的第一个参数（与 swagger paths 一致）。
        鉴权: 依赖客户端已设置 wxid（请求头 X-Wxid 由传输层自动附加）。
        
        请求体 JSON:
          邀请参数：ToWxids为目标用户微信ID列表（逗号分隔），ChatRoomName为群聊ID
        
        Returns:
          transport 解包后的 data（通常为 dict）。
        """
        return await self._t.post('/Group/InviteChatRoomMember', json=body, params=None, timeout=timeout)

    async def group_move_contact_list(self, body: dict[str, Any], *, timeout: Optional[float] = None) -> Any:
        """
        保存或移除通讯录
        
        将指定微信群聊保存到通讯录或从中移除
        
        路径: 见本函数内 self._t.post 的第一个参数（与 swagger paths 一致）。
        鉴权: 依赖客户端已设置 wxid（请求头 X-Wxid 由传输层自动附加）。
        
        请求体 JSON:
          操作参数：Gid为群聊ID，Val为操作值（3添加，2移除）
        
        Returns:
          transport 解包后的 data（通常为 dict）。
        """
        return await self._t.post('/Group/MoveContactList', json=body, params=None, timeout=timeout)

    async def group_operate_chat_room_admin(self, body: dict[str, Any], *, timeout: Optional[float] = None) -> Any:
        """
        群管理操作
        
        执行群聊管理操作，包括添加、删除或转让管理员
        
        路径: 见本函数内 self._t.post 的第一个参数（与 swagger paths 一致）。
        鉴权: 依赖客户端已设置 wxid（请求头 X-Wxid 由传输层自动附加）。
        
        请求体 JSON:
          管理参数：Gid为群聊ID，ToWxids为目标用户微信ID列表（逗号分隔，仅用于添加/删除），Val为操作值（1添加，2删除，3转让）
        
        Returns:
          transport 解包后的 data（通常为 dict）。
        """
        return await self._t.post('/Group/OperateChatRoomAdmin', json=body, params=None, timeout=timeout)

    async def group_quit(self, body: dict[str, Any], *, timeout: Optional[float] = None) -> Any:
        """
        退出群聊
        
        退出指定的微信群聊
        
        路径: 见本函数内 self._t.post 的第一个参数（与 swagger paths 一致）。
        鉴权: 依赖客户端已设置 wxid（请求头 X-Wxid 由传输层自动附加）。
        
        请求体 JSON:
          退出参数：Gid为群聊ID
        
        Returns:
          transport 解包后的 data（通常为 dict）。
        """
        return await self._t.post('/Group/Quit', json=body, params=None, timeout=timeout)

    async def group_scan_into_group(self, body: dict[str, Any], *, timeout: Optional[float] = None) -> Any:
        """
        扫码加入群聊
        
        通过群聊二维码链接加入微信群聊
        
        路径: 见本函数内 self._t.post 的第一个参数（与 swagger paths 一致）。
        鉴权: 依赖客户端已设置 wxid（请求头 X-Wxid 由传输层自动附加）。
        
        请求体 JSON:
          加入参数：Url为群聊二维码链接
        
        Returns:
          transport 解包后的 data（通常为 dict）。
        """
        return await self._t.post('/Group/ScanIntoGroup', json=body, params=None, timeout=timeout)

    async def group_scan_into_group_enterprise(self, body: dict[str, Any], *, timeout: Optional[float] = None) -> Any:
        """
        扫码加入企业群聊
        
        通过二维码链接加入微信企业群聊
        
        路径: 见本函数内 self._t.post 的第一个参数（与 swagger paths 一致）。
        鉴权: 依赖客户端已设置 wxid（请求头 X-Wxid 由传输层自动附加）。
        
        请求体 JSON:
          加入参数：Url为企业群聊二维码链接
        
        Returns:
          transport 解包后的 data（通常为 dict）。
        """
        return await self._t.post('/Group/ScanIntoGroupEnterprise', json=body, params=None, timeout=timeout)

    async def group_set_chat_room_announcement(self, body: dict[str, Any], *, timeout: Optional[float] = None) -> Any:
        """
        设置群公告
        
        为指定微信群聊设置公告内容
        
        路径: 见本函数内 self._t.post 的第一个参数（与 swagger paths 一致）。
        鉴权: 依赖客户端已设置 wxid（请求头 X-Wxid 由传输层自动附加）。
        
        请求体 JSON:
          公告参数：Gid为群聊ID，Content为公告内容
        
        Returns:
          transport 解包后的 data（通常为 dict）。
        """
        return await self._t.post('/Group/SetChatRoomAnnouncement', json=body, params=None, timeout=timeout)

    async def group_set_chat_room_name(self, body: dict[str, Any], *, timeout: Optional[float] = None) -> Any:
        """
        设置群聊名称
        
        为指定微信群聊设置名称
        
        路径: 见本函数内 self._t.post 的第一个参数（与 swagger paths 一致）。
        鉴权: 依赖客户端已设置 wxid（请求头 X-Wxid 由传输层自动附加）。
        
        请求体 JSON:
          名称参数：Gid为群聊ID，Content为群聊名称
        
        Returns:
          transport 解包后的 data（通常为 dict）。
        """
        return await self._t.post('/Group/SetChatRoomName', json=body, params=None, timeout=timeout)

    async def group_set_chat_room_remarks(self, body: dict[str, Any], *, timeout: Optional[float] = None) -> Any:
        """
        设置群聊备注
        
        为指定微信群聊设置备注（仅自己可见）
        
        路径: 见本函数内 self._t.post 的第一个参数（与 swagger paths 一致）。
        鉴权: 依赖客户端已设置 wxid（请求头 X-Wxid 由传输层自动附加）。
        
        请求体 JSON:
          备注参数：Gid为群聊ID，Content为备注内容
        
        Returns:
          transport 解包后的 data（通常为 dict）。
        """
        return await self._t.post('/Group/SetChatRoomRemarks', json=body, params=None, timeout=timeout)


class LabelApi:
    """本组接口与 Swagger 中对应 Tag 一致，各方法含中文说明。"""

    def __init__(self, transport: AsyncHTTPTransport) -> None:
        self._t = transport

    async def label_add(self, body: dict[str, Any], *, timeout: Optional[float] = None) -> Any:
        """
        添加标签
        
        创建新的微信标签
        
        路径: 见本函数内 self._t.post 的第一个参数（与 swagger paths 一致）。
        鉴权: 依赖客户端已设置 wxid（请求头 X-Wxid 由传输层自动附加）。
        
        请求体 JSON:
          添加参数：LabelName为标签名称
        
        Returns:
          transport 解包后的 data（通常为 dict）。
        """
        return await self._t.post('/Label/Add', json=body, params=None, timeout=timeout)

    async def label_delete(self, body: dict[str, Any], *, timeout: Optional[float] = None) -> Any:
        """
        删除标签
        
        删除指定的微信标签
        
        路径: 见本函数内 self._t.post 的第一个参数（与 swagger paths 一致）。
        鉴权: 依赖客户端已设置 wxid（请求头 X-Wxid 由传输层自动附加）。
        
        请求体 JSON:
          删除参数：LabelID为标签ID
        
        Returns:
          transport 解包后的 data（通常为 dict）。
        """
        return await self._t.post('/Label/Delete', json=body, params=None, timeout=timeout)

    async def label_get_list(self, *, timeout: Optional[float] = None) -> Any:
        """
        获取标签列表
        
        获取用户的微信标签列表
        
        路径: 见本函数内 self._t.post 的第一个参数（与 swagger paths 一致）。
        鉴权: 依赖客户端已设置 wxid（请求头 X-Wxid 由传输层自动附加）。
        
        Returns:
          transport 解包后的 data（通常为 dict）。
        """
        return await self._t.post('/Label/GetList', json=None, params=None, timeout=timeout)

    async def label_update_list(self, body: dict[str, Any], *, timeout: Optional[float] = None) -> Any:
        """
        更新标签成员
        
        更新微信标签的成员列表
        
        路径: 见本函数内 self._t.post 的第一个参数（与 swagger paths 一致）。
        鉴权: 依赖客户端已设置 wxid（请求头 X-Wxid 由传输层自动附加）。
        
        请求体 JSON:
          更新参数：LabelID为标签ID，ToWxids为目标用户微信ID列表（逗号分隔）
        
        Returns:
          transport 解包后的 data（通常为 dict）。
        """
        return await self._t.post('/Label/UpdateList', json=body, params=None, timeout=timeout)

    async def label_update_name(self, body: dict[str, Any], *, timeout: Optional[float] = None) -> Any:
        """
        修改标签名称
        
        修改指定微信标签的名称
        
        路径: 见本函数内 self._t.post 的第一个参数（与 swagger paths 一致）。
        鉴权: 依赖客户端已设置 wxid（请求头 X-Wxid 由传输层自动附加）。
        
        请求体 JSON:
          修改参数：LabelID为标签ID，NewName为新标签名称
        
        Returns:
          transport 解包后的 data（通常为 dict）。
        """
        return await self._t.post('/Label/UpdateName', json=body, params=None, timeout=timeout)


class LoginApi:
    """本组接口与 Swagger 中对应 Tag 一致，各方法含中文说明。"""

    def __init__(self, transport: AsyncHTTPTransport) -> None:
        self._t = transport

    async def login_awaken(self, *, timeout: Optional[float] = None) -> Any:
        """
        唤醒登录
        
        唤醒已存在的登录会话
        
        路径: 见本函数内 self._t.post 的第一个参数（与 swagger paths 一致）。
        鉴权: 依赖客户端已设置 wxid（请求头 X-Wxid 由传输层自动附加）。
        
        Returns:
          transport 解包后的 data（通常为 dict）。
        """
        return await self._t.post('/Login/Awaken', json=None, params=None, timeout=timeout)

    async def login_heart_beat(self, *, timeout: float = 45.0) -> Any:
        """
        发送心跳包
        
        发送心跳包以保持登录会话活跃
        
        路径: 见本函数内 self._t.post 的第一个参数（与 swagger paths 一致）。
        鉴权: 依赖客户端已设置 wxid（请求头 X-Wxid 由传输层自动附加）。
        
        Returns:
          transport 解包后的 data（通常为 dict）。
        """
        return await self._t.post('/Login/HeartBeat', json=None, params=None, timeout=timeout)

    async def login_log_out(self, *, timeout: Optional[float] = None) -> Any:
        """
        退出登录
        
        退出当前微信登录会话
        
        路径: 见本函数内 self._t.post 的第一个参数（与 swagger paths 一致）。
        鉴权: 依赖客户端已设置 wxid（请求头 X-Wxid 由传输层自动附加）。
        
        Returns:
          transport 解包后的 data（通常为 dict）。
        """
        return await self._t.post('/Login/LogOut', json=None, params=None, timeout=timeout)

    async def login_long_link_create(self, *, timeout: Optional[float] = None) -> Any:
        """
        创建长链接
        
        发送长连接心跳包以维持长时间会话
        
        路径: 见本函数内 self._t.post 的第一个参数（与 swagger paths 一致）。
        鉴权: 依赖客户端已设置 wxid（请求头 X-Wxid 由传输层自动附加）。
        
        Returns:
          transport 解包后的 data（通常为 dict）。
        """
        return await self._t.post('/Login/LongLinkCreate', json=None, params=None, timeout=timeout)

    async def login_long_query(self, *, timeout: Optional[float] = None) -> Any:
        """
        查询长连接状态
        
        查询当前长连接的状态
        
        路径: 见本函数内 self._t.post 的第一个参数（与 swagger paths 一致）。
        鉴权: 依赖客户端已设置 wxid（请求头 X-Wxid 由传输层自动附加）。
        
        Returns:
          transport 解包后的 data（通常为 dict）。
        """
        return await self._t.post('/Login/LongQuery', json=None, params=None, timeout=timeout)

    async def login_long_remove(self, *, timeout: Optional[float] = None) -> Any:
        """
        断开长连接
        
        断开当前的长连接会话
        
        路径: 见本函数内 self._t.post 的第一个参数（与 swagger paths 一致）。
        鉴权: 依赖客户端已设置 wxid（请求头 X-Wxid 由传输层自动附加）。
        
        Returns:
          transport 解包后的 data（通常为 dict）。
        """
        return await self._t.post('/Login/LongRemove', json=None, params=None, timeout=timeout)

    async def login_qrcheck(self, uuid: str, *, timeout: Optional[float] = None) -> Any:
        """
        检测二维码状态
        
        检查二维码的扫描状态，确认是否登录成功
        
        路径: 见本函数内 self._t.post 的第一个参数（与 swagger paths 一致）。
        鉴权: 依赖客户端已设置 wxid（请求头 X-Wxid 由传输层自动附加）。
        
        Query 参数:
          - uuid（uuid，必填） — 二维码的UUID，来自获取二维码接口的返回
        
        Returns:
          transport 解包后的 data（通常为 dict）。
        """
        params: dict[str, Any] = {}
        params["uuid"] = uuid
        return await self._t.post('/Login/QRCheck', json=None, params=params, timeout=timeout)

    async def login_qrget(self, body: dict[str, Any], *, timeout: Optional[float] = None) -> Any:
        """
        获取登录二维码
        
        获取微信登录所需的二维码，可选择是否使用代理
        
        路径: 见本函数内 self._t.post 的第一个参数（与 swagger paths 一致）。
        鉴权: 依赖客户端已设置 wxid（请求头 X-Wxid 由传输层自动附加）。
        
        请求体 JSON:
          二维码请求参数：Proxy为代理地址（不使用代理时留空）
        
        Returns:
          transport 解包后的 data（通常为 dict）。
        """
        return await self._t.post('/Login/QRGet', json=body, params=None, timeout=timeout)

    async def login_reportclientcheck(self, *, timeout: Optional[float] = None) -> Any:
        """
        Reportclientcheck
        
        定时上报客户端环境（一天一次）
        
        路径: 见本函数内 self._t.post 的第一个参数（与 swagger paths 一致）。
        鉴权: 依赖客户端已设置 wxid（请求头 X-Wxid 由传输层自动附加）。
        
        Returns:
          transport 解包后的 data（通常为 dict）。
        """
        return await self._t.post('/Login/Reportclientcheck', json=None, params=None, timeout=timeout)

    async def login_sec_auto_auth(self, *, timeout: Optional[float] = None) -> Any:
        """
        二次登录
        
        使用已登录的微信ID进行二次自动登录
        
        路径: 见本函数内 self._t.post 的第一个参数（与 swagger paths 一致）。
        鉴权: 依赖客户端已设置 wxid（请求头 X-Wxid 由传输层自动附加）。
        
        Returns:
          transport 解包后的 data（通常为 dict）。
        """
        return await self._t.post('/Login/SecAutoAuth', json=None, params=None, timeout=timeout)


class MmSnsApi:
    """本组接口与 Swagger 中对应 Tag 一致，各方法含中文说明。"""

    def __init__(self, transport: AsyncHTTPTransport) -> None:
        self._t = transport

    async def mm_sns_comment(self, body: dict[str, Any], *, timeout: Optional[float] = None) -> Any:
        """
        朋友圈点赞或评论
        
        对朋友圈内容进行点赞或评论
        
        路径: 见本函数内 self._t.post 的第一个参数（与 swagger paths 一致）。
        鉴权: 依赖客户端已设置 wxid（请求头 X-Wxid 由传输层自动附加）。
        
        请求体 JSON:
          操作参数：Id为朋友圈内容ID，Type为操作类型（1点赞，2文本评论，3消息评论，4with，5陌生人点赞），Content为评论内容（Type为2或3时有效），ReplyCommnetId为回复的评论ID（Type为2或3时有效）
        
        Returns:
          transport 解包后的 data（通常为 dict）。
        """
        return await self._t.post('/MmSns/Comment', json=body, params=None, timeout=timeout)

    async def mm_sns_get_detail(self, body: dict[str, Any], *, timeout: Optional[float] = None) -> Any:
        """
        获取特定人朋友圈
        
        获取指定用户的微信朋友圈动态
        
        路径: 见本函数内 self._t.post 的第一个参数（与 swagger paths 一致）。
        鉴权: 依赖客户端已设置 wxid（请求头 X-Wxid 由传输层自动附加）。
        
        请求体 JSON:
          查询参数：Towxid为目标用户微信ID，Maxid为最大朋友圈ID（首次请求填0），Fristpagemd5为首页MD5值（首次请求留空）
        
        Returns:
          transport 解包后的 data（通常为 dict）。
        """
        return await self._t.post('/MmSns/GetDetail', json=body, params=None, timeout=timeout)

    async def mm_sns_get_id_detail(self, body: dict[str, Any], *, timeout: Optional[float] = None) -> Any:
        """
        获取朋友圈内容详情
        
        获取指定朋友圈内容的详细信息
        
        路径: 见本函数内 self._t.post 的第一个参数（与 swagger paths 一致）。
        鉴权: 依赖客户端已设置 wxid（请求头 X-Wxid 由传输层自动附加）。
        
        请求体 JSON:
          查询参数：Towxid为发布者微信ID，Id为朋友圈内容ID
        
        Returns:
          transport 解包后的 data（通常为 dict）。
        """
        return await self._t.post('/MmSns/GetIdDetail', json=body, params=None, timeout=timeout)

    async def mm_sns_get_list(self, body: dict[str, Any], *, timeout: Optional[float] = None) -> Any:
        """
        获取朋友圈首页列表
        
        获取微信朋友圈首页的动态列表
        
        路径: 见本函数内 self._t.post 的第一个参数（与 swagger paths 一致）。
        鉴权: 依赖客户端已设置 wxid（请求头 X-Wxid 由传输层自动附加）。
        
        请求体 JSON:
          列表参数：Maxid为最大朋友圈ID（首次请求填0），Fristpagemd5为首页MD5值（首次请求留空）
        
        Returns:
          transport 解包后的 data（通常为 dict）。
        """
        return await self._t.post('/MmSns/GetList', json=body, params=None, timeout=timeout)

    async def mm_sns_mm_sns_post(self, body: dict[str, Any], *, timeout: Optional[float] = None) -> Any:
        """
        发布朋友圈
        
        发布新的微信朋友圈内容
        
        路径: 见本函数内 self._t.post 的第一个参数（与 swagger paths 一致）。
        鉴权: 依赖客户端已设置 wxid（请求头 X-Wxid 由传输层自动附加）。
        
        请求体 JSON:
          发布参数：Content为朋友圈内容（需自行构造XML），BlackList为黑名单用户列表（逗号分隔），WithUserList为指定可见用户列表（逗号分隔）
        
        Returns:
          transport 解包后的 data（通常为 dict）。
        """
        return await self._t.post('/MmSns/MmSnsPost', json=body, params=None, timeout=timeout)

    async def mm_sns_mm_sns_sync(self, body: dict[str, Any], *, timeout: Optional[float] = None) -> Any:
        """
        朋友圈同步
        
        同步用户的微信朋友圈数据
        
        路径: 见本函数内 self._t.post 的第一个参数（与 swagger paths 一致）。
        鉴权: 依赖客户端已设置 wxid（请求头 X-Wxid 由传输层自动附加）。
        
        请求体 JSON:
          同步参数：Synckey为同步密钥（首次同步可留空）
        
        Returns:
          transport 解包后的 data（通常为 dict）。
        """
        return await self._t.post('/MmSns/MmSnsSync', json=body, params=None, timeout=timeout)

    async def mm_sns_operation(self, body: dict[str, Any], *, timeout: Optional[float] = None) -> Any:
        """
        朋友圈操作
        
        对朋友圈内容执行操作（如删除、设置隐私等）
        
        路径: 见本函数内 self._t.post 的第一个参数（与 swagger paths 一致）。
        鉴权: 依赖客户端已设置 wxid（请求头 X-Wxid 由传输层自动附加）。
        
        请求体 JSON:
          操作参数：Id为朋友圈内容ID，Type为操作类型（1删除朋友圈，2设为隐私，3设为公开，4删除评论，5取消点赞），CommnetId为评论ID（Type为4时有效）
        
        Returns:
          transport 解包后的 data（通常为 dict）。
        """
        return await self._t.post('/MmSns/Operation', json=body, params=None, timeout=timeout)

    async def mm_sns_privacy_settings(self, body: dict[str, Any], *, timeout: Optional[float] = None) -> Any:
        """
        朋友圈权限设置
        
        设置微信朋友圈的权限
        
        路径: 见本函数内 self._t.post 的第一个参数（与 swagger paths 一致）。
        鉴权: 依赖客户端已设置 wxid（请求头 X-Wxid 由传输层自动附加）。
        
        请求体 JSON:
          设置参数：Function为功能代码（具体值需联系客服获取），Value为设置值
        
        Returns:
          transport 解包后的 data（通常为 dict）。
        """
        return await self._t.post('/MmSns/PrivacySettings', json=body, params=None, timeout=timeout)

    async def mm_sns_upload(self, body: dict[str, Any], *, timeout: Optional[float] = None) -> Any:
        """
        朋友圈上传
        
        上传图片或视频到微信朋友圈
        
        路径: 见本函数内 self._t.post 的第一个参数（与 swagger paths 一致）。
        鉴权: 依赖客户端已设置 wxid（请求头 X-Wxid 由传输层自动附加）。
        
        请求体 JSON:
          上传参数：Base64为图片或视频的Base64编码数据
        
        Returns:
          transport 解包后的 data（通常为 dict）。
        """
        return await self._t.post('/MmSns/Upload', json=body, params=None, timeout=timeout)


class MsgApi:
    """本组接口与 Swagger 中对应 Tag 一致，各方法含中文说明。"""

    def __init__(self, transport: AsyncHTTPTransport) -> None:
        self._t = transport

    async def msg_revoke(self, body: dict[str, Any], *, timeout: Optional[float] = None) -> Any:
        """
        撤回消息
        
        撤回已发送的消息，需提供消息ID
        
        路径: 见本函数内 self._t.post 的第一个参数（与 swagger paths 一致）。
        鉴权: 依赖客户端已设置 wxid（请求头 X-Wxid 由传输层自动附加）。
        
        请求体 JSON:
          撤回参数：MsgId为要撤回的消息ID
        
        Returns:
          transport 解包后的 data（通常为 dict）。
        """
        return await self._t.post('/Msg/Revoke', json=body, params=None, timeout=timeout)

    async def msg_send_app(self, body: dict[str, Any], *, timeout: Optional[float] = None) -> Any:
        """
        发送小程序消息
        
        发送小程序消息，需提供小程序的XML数据和类型
        
        路径: 见本函数内 self._t.post 的第一个参数（与 swagger paths 一致）。
        鉴权: 依赖客户端已设置 wxid（请求头 X-Wxid 由传输层自动附加）。
        
        请求体 JSON:
          小程序消息参数：ToWxid为接收者微信ID，Xml为小程序XML数据，Type为消息类型（根据场景设置）
        
        Returns:
          transport 解包后的 data（通常为 dict）。
        """
        return await self._t.post('/Msg/SendApp', json=body, params=None, timeout=timeout)

    async def msg_send_cdnfile(self, body: dict[str, Any], *, timeout: Optional[float] = None) -> Any:
        """
        发送CDN文件消息
        
        转发CDN文件消息，需提供文件的XML数据
        
        路径: 见本函数内 self._t.post 的第一个参数（与 swagger paths 一致）。
        鉴权: 依赖客户端已设置 wxid（请求头 X-Wxid 由传输层自动附加）。
        
        请求体 JSON:
          CDN文件参数：ToWxid为接收者微信ID，Content为文件消息的XML数据
        
        Returns:
          transport 解包后的 data（通常为 dict）。
        """
        return await self._t.post('/Msg/SendCDNFile', json=body, params=None, timeout=timeout)

    async def msg_send_cdnimg(self, body: dict[str, Any], *, timeout: Optional[float] = None) -> Any:
        """
        发送CDN图片消息
        
        转发CDN图片消息，需提供图片的XML数据
        
        路径: 见本函数内 self._t.post 的第一个参数（与 swagger paths 一致）。
        鉴权: 依赖客户端已设置 wxid（请求头 X-Wxid 由传输层自动附加）。
        
        请求体 JSON:
          CDN图片参数：ToWxid为接收者微信ID，Content为图片消息的XML数据
        
        Returns:
          transport 解包后的 data（通常为 dict）。
        """
        return await self._t.post('/Msg/SendCDNImg', json=body, params=None, timeout=timeout)

    async def msg_send_cdnvideo(self, body: dict[str, Any], *, timeout: Optional[float] = None) -> Any:
        """
        发送CDN视频消息
        
        转发CDN视频消息，需提供视频的XML数据
        
        路径: 见本函数内 self._t.post 的第一个参数（与 swagger paths 一致）。
        鉴权: 依赖客户端已设置 wxid（请求头 X-Wxid 由传输层自动附加）。
        
        请求体 JSON:
          CDN视频参数：ToWxid为接收者微信ID，Content为视频消息的XML数据
        
        Returns:
          transport 解包后的 data（通常为 dict）。
        """
        return await self._t.post('/Msg/SendCDNVideo', json=body, params=None, timeout=timeout)

    async def msg_send_emoji(self, body: dict[str, Any], *, timeout: Optional[float] = None) -> Any:
        """
        发送表情消息
        
        发送表情消息，需提供表情数据和MD5校验值
        
        路径: 见本函数内 self._t.post 的第一个参数（与 swagger paths 一致）。
        鉴权: 依赖客户端已设置 wxid（请求头 X-Wxid 由传输层自动附加）。
        
        请求体 JSON:
          表情消息参数：ToWxid为接收者微信ID，TotalLen为表情数据长度，Md5为表情数据的MD5校验值
        
        Returns:
          transport 解包后的 data（通常为 dict）。
        """
        return await self._t.post('/Msg/SendEmoji', json=body, params=None, timeout=timeout)

    async def msg_send_quote(self, body: dict[str, Any], *, timeout: Optional[float] = None) -> Any:
        """
        发送引用文本消息
        
        发送引用文本消息，支持引用其他用户的消息内容
        
        路径: 见本函数内 self._t.post 的第一个参数（与 swagger paths 一致）。
        鉴权: 依赖客户端已设置 wxid（请求头 X-Wxid 由传输层自动附加）。
        
        请求体 JSON:
          引用消息参数：Fromusr为被引用人的微信ID，Displayname为被引用人名称，NewMsgId为引用人消息的ID，MsgContent为新消息内容，QuoteContent为引用内容
        
        Returns:
          transport 解包后的 data（通常为 dict）。
        """
        return await self._t.post('/Msg/SendQuote', json=body, params=None, timeout=timeout)

    async def msg_send_txt(self, body: dict[str, Any], *, timeout: Optional[float] = None) -> Any:
        """
        发送文本消息
        
        发送文本消息，支持单聊或群聊，可@群成员
        
        路径: 见本函数内 self._t.post 的第一个参数（与 swagger paths 一致）。
        鉴权: 依赖客户端已设置 wxid（请求头 X-Wxid 由传输层自动附加）。
        
        请求体 JSON:
          文本消息参数：ToWxid为接收者微信ID（单聊）或群ID（群聊），Content为消息内容，At为群聊@的微信ID列表（逗号分隔）
        
        Returns:
          transport 解包后的 data（通常为 dict）。
        """
        return await self._t.post('/Msg/SendTxt', json=body, params=None, timeout=timeout)

    async def msg_send_video(self, body: dict[str, Any], *, timeout: Optional[float] = None) -> Any:
        """
        发送视频消息
        
        发送视频消息，需提供视频和封面的Base64编码数据
        
        路径: 见本函数内 self._t.post 的第一个参数（与 swagger paths 一致）。
        鉴权: 依赖客户端已设置 wxid（请求头 X-Wxid 由传输层自动附加）。
        
        请求体 JSON:
          视频消息参数：ToWxid为接收者微信ID，PlayLength为视频时长（秒），Base64为视频的Base64编码数据，ImageBase64为封面的Base64编码数据
        
        Returns:
          transport 解包后的 data（通常为 dict）。
        """
        return await self._t.post('/Msg/SendVideo', json=body, params=None, timeout=timeout)

    async def msg_send_voice(self, body: dict[str, Any], *, timeout: Optional[float] = None) -> Any:
        """
        发送语音消息
        
        发送语音消息，需指定语音格式和时长
        
        路径: 见本函数内 self._t.post 的第一个参数（与 swagger paths 一致）。
        鉴权: 依赖客户端已设置 wxid（请求头 X-Wxid 由传输层自动附加）。
        
        请求体 JSON:
          语音消息参数：ToWxid为接收者微信ID，Base64为语音的Base64编码数据，Type为语音格式（AMR=0, MP3=2, SILK=4, SPEEX=1, WAVE=3），VoiceTime为语音时长（毫秒，1000为一秒）
        
        Returns:
          transport 解包后的 data（通常为 dict）。
        """
        return await self._t.post('/Msg/SendVoice', json=body, params=None, timeout=timeout)

    async def msg_share_card(self, body: dict[str, Any], *, timeout: Optional[float] = None) -> Any:
        """
        分享名片
        
        分享微信名片，需提供名片相关信息
        
        路径: 见本函数内 self._t.post 的第一个参数（与 swagger paths 一致）。
        鉴权: 依赖客户端已设置 wxid（请求头 X-Wxid 由传输层自动附加）。
        
        请求体 JSON:
          名片参数：ToWxid为接收者微信ID，CardWxId为名片微信ID，CardNickName为名片昵称，CardAlias为名片别名
        
        Returns:
          transport 解包后的 data（通常为 dict）。
        """
        return await self._t.post('/Msg/ShareCard', json=body, params=None, timeout=timeout)

    async def msg_share_link(self, body: dict[str, Any], *, timeout: Optional[float] = None) -> Any:
        """
        发送分享链接消息
        
        发送包含标题、描述、URL和缩略图的分享链接消息
        
        路径: 见本函数内 self._t.post 的第一个参数（与 swagger paths 一致）。
        鉴权: 依赖客户端已设置 wxid（请求头 X-Wxid 由传输层自动附加）。
        
        请求体 JSON:
          分享链接参数：ToWxid为接收者微信ID，Title为链接标题，Desc为链接描述，Url为跳转地址，ThumbUrl为缩略图URL
        
        Returns:
          transport 解包后的 data（通常为 dict）。
        """
        return await self._t.post('/Msg/ShareLink', json=body, params=None, timeout=timeout)

    async def msg_share_location(self, body: dict[str, Any], *, timeout: Optional[float] = None) -> Any:
        """
        分享位置
        
        分享地理位置信息，需提供经纬度和位置描述
        
        路径: 见本函数内 self._t.post 的第一个参数（与 swagger paths 一致）。
        鉴权: 依赖客户端已设置 wxid（请求头 X-Wxid 由传输层自动附加）。
        
        请求体 JSON:
          位置参数：ToWxid为接收者微信ID，X为经度，Y为纬度，Scale为地图缩放比例，Label为位置标签，Poiname为位置名称，Infourl为附加信息URL
        
        Returns:
          transport 解包后的 data（通常为 dict）。
        """
        return await self._t.post('/Msg/ShareLocation', json=body, params=None, timeout=timeout)

    async def msg_share_video(self, body: dict[str, Any], *, timeout: Optional[float] = None) -> Any:
        """
        分享视频消息
        
        分享视频消息，需提供视频的XML数据
        
        路径: 见本函数内 self._t.post 的第一个参数（与 swagger paths 一致）。
        鉴权: 依赖客户端已设置 wxid（请求头 X-Wxid 由传输层自动附加）。
        
        请求体 JSON:
          视频分享参数：ToWxid为接收者微信ID，Xml为视频消息的XML数据
        
        Returns:
          transport 解包后的 data（通常为 dict）。
        """
        return await self._t.post('/Msg/ShareVideo', json=body, params=None, timeout=timeout)

    async def msg_sync(self, *, timeout: float = 180.0) -> Any:
        """
        同步消息
        
        同步用户的微信消息，获取最新消息记录
        
        路径: 见本函数内 self._t.post 的第一个参数（与 swagger paths 一致）。
        鉴权: 依赖客户端已设置 wxid（请求头 X-Wxid 由传输层自动附加）。
        
        Returns:
          transport 解包后的 data（通常为 dict）。
        """
        return await self._t.post('/Msg/Sync', json=None, params=None, timeout=timeout)

    async def msg_upload_img(self, body: dict[str, Any], *, timeout: Optional[float] = None) -> Any:
        """
        发送图片消息
        
        发送图片消息，需提供Base64编码的图片数据
        
        路径: 见本函数内 self._t.post 的第一个参数（与 swagger paths 一致）。
        鉴权: 依赖客户端已设置 wxid（请求头 X-Wxid 由传输层自动附加）。
        
        请求体 JSON:
          图片消息参数：ToWxid为接收者微信ID，Base64为图片的Base64编码数据
        
        Returns:
          transport 解包后的 data（通常为 dict）。
        """
        return await self._t.post('/Msg/UploadImg', json=body, params=None, timeout=timeout)


class OfficialApi:
    """本组接口与 Swagger 中对应 Tag 一致，各方法含中文说明。"""

    def __init__(self, transport: AsyncHTTPTransport) -> None:
        self._t = transport

    async def official_biz_profile_v2(self, body: dict[str, Any], *, timeout: Optional[float] = None) -> Any:
        """
        获取公众号文章列表
        
        获取指定公众号历史文章列表
        
        路径: 见本函数内 self._t.post 的第一个参数（与 swagger paths 一致）。
        鉴权: 依赖客户端已设置 wxid（请求头 X-Wxid 由传输层自动附加）。
        
        请求体 JSON:
          参数：Wxid、公众号biz用户名、分页参数等
        
        Returns:
          transport 解包后的 data（通常为 dict）。
        """
        return await self._t.post('/Official/BizProfileV2', json=body, params=None, timeout=timeout)

    async def official_follow(self, body: dict[str, Any], *, timeout: Optional[float] = None) -> Any:
        """
        关注公众号
        
        用户发起关注公众号操作
        
        路径: 见本函数内 self._t.post 的第一个参数（与 swagger paths 一致）。
        鉴权: 依赖客户端已设置 wxid（请求头 X-Wxid 由传输层自动附加）。
        
        请求体 JSON:
          关注参数：Appid为公众号AppID
        
        Returns:
          transport 解包后的 data（通常为 dict）。
        """
        return await self._t.post('/Official/Follow', json=body, params=None, timeout=timeout)

    async def official_get_app_msg_ext(self, body: dict[str, Any], *, timeout: Optional[float] = None) -> Any:
        """
        阅读文章
        
        模拟用户行为读取文章详情并触发阅读
        
        路径: 见本函数内 self._t.post 的第一个参数（与 swagger paths 一致）。
        鉴权: 依赖客户端已设置 wxid（请求头 X-Wxid 由传输层自动附加）。
        
        请求体 JSON:
          参数：Url为文章地址
        
        Returns:
          transport 解包后的 data（通常为 dict）。
        """
        return await self._t.post('/Official/GetAppMsgExt', json=body, params=None, timeout=timeout)

    async def official_get_app_msg_ext_like(self, body: dict[str, Any], *, timeout: Optional[float] = None) -> Any:
        """
        点赞文章
        
        点赞指定的公众号文章
        
        路径: 见本函数内 self._t.post 的第一个参数（与 swagger paths 一致）。
        鉴权: 依赖客户端已设置 wxid（请求头 X-Wxid 由传输层自动附加）。
        
        请求体 JSON:
          参数：Url为文章地址
        
        Returns:
          transport 解包后的 data（通常为 dict）。
        """
        return await self._t.post('/Official/GetAppMsgExtLike', json=body, params=None, timeout=timeout)

    async def official_get_comment_data(self, body: dict[str, Any], *, timeout: Optional[float] = None) -> Any:
        """
        获取文章评论数据
        
        获取公众号文章的评论内容或评论数
        
        路径: 见本函数内 self._t.post 的第一个参数（与 swagger paths 一致）。
        鉴权: 依赖客户端已设置 wxid（请求头 X-Wxid 由传输层自动附加）。
        
        请求体 JSON:
          参数：Url为文章地址
        
        Returns:
          transport 解包后的 data（通常为 dict）。
        """
        return await self._t.post('/Official/GetCommentData', json=body, params=None, timeout=timeout)

    async def official_get_read_data(self, body: dict[str, Any], *, timeout: Optional[float] = None) -> Any:
        """
        获取文章阅读数据
        
        获取指定公众号文章的阅读数等统计信息
        
        路径: 见本函数内 self._t.post 的第一个参数（与 swagger paths 一致）。
        鉴权: 依赖客户端已设置 wxid（请求头 X-Wxid 由传输层自动附加）。
        
        请求体 JSON:
          参数：Url为文章地址
        
        Returns:
          transport 解包后的 data（通常为 dict）。
        """
        return await self._t.post('/Official/GetReadData', json=body, params=None, timeout=timeout)

    async def official_jsapipre_verify(self, body: dict[str, Any], *, timeout: Optional[float] = None) -> Any:
        """
        JSAPI预验证
        
        获取公众号网页JSAPI签名
        
        路径: 见本函数内 self._t.post 的第一个参数（与 swagger paths 一致）。
        鉴权: 依赖客户端已设置 wxid（请求头 X-Wxid 由传输层自动附加）。
        
        请求体 JSON:
          参数：Url为网页地址，Appid为公众号AppID
        
        Returns:
          transport 解包后的 data（通常为 dict）。
        """
        return await self._t.post('/Official/JSAPIPreVerify', json=body, params=None, timeout=timeout)

    async def official_mp_get_a8key(self, body: dict[str, Any], *, timeout: Optional[float] = None) -> Any:
        """
        获取文章Key和Uin
        
        用于获取文章阅读权限所需的key和uin信息
        
        路径: 见本函数内 self._t.post 的第一个参数（与 swagger paths 一致）。
        鉴权: 依赖客户端已设置 wxid（请求头 X-Wxid 由传输层自动附加）。
        
        请求体 JSON:
          参数：Url为文章地址
        
        Returns:
          transport 解包后的 data（通常为 dict）。
        """
        return await self._t.post('/Official/MpGetA8Key', json=body, params=None, timeout=timeout)

    async def official_oauth_authorize(self, body: dict[str, Any], *, timeout: Optional[float] = None) -> Any:
        """
        OAuth授权
        
        获取公众号网页OAuth授权信息
        
        路径: 见本函数内 self._t.post 的第一个参数（与 swagger paths 一致）。
        鉴权: 依赖客户端已设置 wxid（请求头 X-Wxid 由传输层自动附加）。
        
        请求体 JSON:
          参数：Url为授权页面链接，Appid为公众号AppID
        
        Returns:
          transport 解包后的 data（通常为 dict）。
        """
        return await self._t.post('/Official/OauthAuthorize', json=body, params=None, timeout=timeout)

    async def official_quit(self, body: dict[str, Any], *, timeout: Optional[float] = None) -> Any:
        """
        取消关注公众号
        
        用户发起取消关注操作
        
        路径: 见本函数内 self._t.post 的第一个参数（与 swagger paths 一致）。
        鉴权: 依赖客户端已设置 wxid（请求头 X-Wxid 由传输层自动附加）。
        
        请求体 JSON:
          取消关注参数：Appid为公众号AppID
        
        Returns:
          transport 解包后的 data（通常为 dict）。
        """
        return await self._t.post('/Official/Quit', json=body, params=None, timeout=timeout)


class OtherApi:
    """本组接口与 Swagger 中对应 Tag 一致，各方法含中文说明。"""

    def __init__(self, transport: AsyncHTTPTransport) -> None:
        self._t = transport

    async def other_cdn_download_image(self, body: dict[str, Any], *, timeout: Optional[float] = None) -> Any:
        """
        CDN下载高清图片
        
        通过CDN下载微信高清图片
        
        路径: 见本函数内 self._t.post 的第一个参数（与 swagger paths 一致）。
        鉴权: 依赖客户端已设置 wxid（请求头 X-Wxid 由传输层自动附加）。
        
        请求体 JSON:
          下载参数：FileNo为文件编号，FileAesKey为文件AES密钥
        
        Returns:
          transport 解包后的 data（通常为 dict）。
        """
        return await self._t.post('/Other/CdnDownloadImage', json=body, params=None, timeout=timeout)

    async def other_download_file(self, body: dict[str, Any], *, timeout: Optional[float] = None) -> Any:
        """
        下载文件
        
        下载微信消息中的文件附件
        
        路径: 见本函数内 self._t.post 的第一个参数（与 swagger paths 一致）。
        鉴权: 依赖客户端已设置 wxid（请求头 X-Wxid 由传输层自动附加）。
        
        请求体 JSON:
          下载参数：AppID为应用ID，AttachId为附件ID，UserName为发送者微信ID，DataLen为文件大小（从XML获取），Section为数据段信息
        
        Returns:
          transport 解包后的 data（通常为 dict）。
        """
        return await self._t.post('/Other/DownloadFile', json=body, params=None, timeout=timeout)

    async def other_download_img(self, body: dict[str, Any], *, timeout: Optional[float] = None) -> Any:
        """
        下载高清图片
        
        下载微信消息中的高清图片
        
        路径: 见本函数内 self._t.post 的第一个参数（与 swagger paths 一致）。
        鉴权: 依赖客户端已设置 wxid（请求头 X-Wxid 由传输层自动附加）。
        
        请求体 JSON:
          下载参数：ToWxid为目标用户微信ID，MsgId为消息ID，DataLen为图片大小（从XML获取），Section为数据段信息，CompressType为压缩类型
        
        Returns:
          transport 解包后的 data（通常为 dict）。
        """
        return await self._t.post('/Other/DownloadImg', json=body, params=None, timeout=timeout)

    async def other_download_video(self, body: dict[str, Any], *, timeout: Optional[float] = None) -> Any:
        """
        下载视频
        
        下载微信消息中的视频
        
        路径: 见本函数内 self._t.post 的第一个参数（与 swagger paths 一致）。
        鉴权: 依赖客户端已设置 wxid（请求头 X-Wxid 由传输层自动附加）。
        
        请求体 JSON:
          下载参数：ToWxid为目标用户微信ID，MsgId为消息ID，DataLen为视频大小（从XML获取），Section为数据段信息，CompressType为压缩类型
        
        Returns:
          transport 解包后的 data（通常为 dict）。
        """
        return await self._t.post('/Other/DownloadVideo', json=body, params=None, timeout=timeout)

    async def other_download_voice(self, body: dict[str, Any], *, timeout: Optional[float] = None) -> Any:
        """
        下载语音
        
        下载微信消息中的语音
        
        路径: 见本函数内 self._t.post 的第一个参数（与 swagger paths 一致）。
        鉴权: 依赖客户端已设置 wxid（请求头 X-Wxid 由传输层自动附加）。
        
        请求体 JSON:
          下载参数：FromUserName为发送者微信ID，MsgId为消息ID，Bufid为语音缓冲区ID，Length为语音数据长度
        
        Returns:
          transport 解包后的 data（通常为 dict）。
        """
        return await self._t.post('/Other/DownloadVoice', json=body, params=None, timeout=timeout)

    async def other_get_a8key(self, body: dict[str, Any], *, timeout: Optional[float] = None) -> Any:
        """
        获取A8Key
        
        获取微信的A8Key，用于特定场景的认证
        
        路径: 见本函数内 self._t.post 的第一个参数（与 swagger paths 一致）。
        鉴权: 依赖客户端已设置 wxid（请求头 X-Wxid 由传输层自动附加）。
        
        请求体 JSON:
          请求参数：OpCode默认为2，Scene默认为4，CodeType默认为19，CodeVersion默认为5，ReqUrl为请求URL，CookieBase64为Cookie数据，NetType为网络类型，Flag为标志位
        
        Returns:
          transport 解包后的 data（通常为 dict）。
        """
        return await self._t.post('/Other/GetA8Key', json=body, params=None, timeout=timeout)

    async def other_get_bound_hard_devices(self, *, timeout: Optional[float] = None) -> Any:
        """
        获取绑定硬件设备
        
        获取用户绑定的微信硬件设备列表
        
        路径: 见本函数内 self._t.post 的第一个参数（与 swagger paths 一致）。
        鉴权: 依赖客户端已设置 wxid（请求头 X-Wxid 由传输层自动附加）。
        
        Returns:
          transport 解包后的 data（通常为 dict）。
        """
        return await self._t.post('/Other/GetBoundHardDevices', json=None, params=None, timeout=timeout)

    async def other_get_cdn_dns(self, *, timeout: Optional[float] = None) -> Any:
        """
        获取CDN服务器DNS信息
        
        获取微信CDN服务器的DNS信息
        
        路径: 见本函数内 self._t.post 的第一个参数（与 swagger paths 一致）。
        鉴权: 依赖客户端已设置 wxid（请求头 X-Wxid 由传输层自动附加）。
        
        Returns:
          transport 解包后的 data（通常为 dict）。
        """
        return await self._t.post('/Other/GetCdnDns', json=None, params=None, timeout=timeout)

    async def other_third_app_grant(self, body: dict[str, Any], *, timeout: Optional[float] = None) -> Any:
        """
        第三方应用授权
        
        授权第三方应用访问微信
        
        路径: 见本函数内 self._t.post 的第一个参数（与 swagger paths 一致）。
        鉴权: 依赖客户端已设置 wxid（请求头 X-Wxid 由传输层自动附加）。
        
        请求体 JSON:
          授权参数：Appid为第三方应用ID
        
        Returns:
          transport 解包后的 data（通常为 dict）。
        """
        return await self._t.post('/Other/ThirdAppGrant', json=body, params=None, timeout=timeout)


class UserApi:
    """本组接口与 Swagger 中对应 Tag 一致，各方法含中文说明。"""

    def __init__(self, transport: AsyncHTTPTransport) -> None:
        self._t = transport

    async def user_get_contact_profile(self, *, timeout: Optional[float] = None) -> Any:
        """
        获取个人信息
        
        获取用户的微信个人信息
        
        路径: 见本函数内 self._t.post 的第一个参数（与 swagger paths 一致）。
        鉴权: 依赖客户端已设置 wxid（请求头 X-Wxid 由传输层自动附加）。
        
        Returns:
          transport 解包后的 data（通常为 dict）。
        """
        return await self._t.post('/User/GetContactProfile', json=None, params=None, timeout=timeout)

    async def user_get_qrcode(self, body: dict[str, Any], *, timeout: Optional[float] = None) -> Any:
        """
        获取个人二维码
        
        获取用户的微信个人二维码
        
        路径: 见本函数内 self._t.post 的第一个参数（与 swagger paths 一致）。
        鉴权: 依赖客户端已设置 wxid（请求头 X-Wxid 由传输层自动附加）。
        
        请求体 JSON:
          查询参数：Style为二维码样式（8为默认样式）
        
        Returns:
          transport 解包后的 data（通常为 dict）。
        """
        return await self._t.post('/User/GetQRCode', json=body, params=None, timeout=timeout)

    async def user_get_user_auth_list(self, body: dict[str, Any], *, timeout: Optional[float] = None) -> Any:
        """
        获取已授权应用列表
        
        获取用户已授权的应用列表
        
        路径: 见本函数内 self._t.post 的第一个参数（与 swagger paths 一致）。
        鉴权: 依赖客户端已设置 wxid（请求头 X-Wxid 由传输层自动附加）。
        
        请求体 JSON:
          查询参数：KeyWord为搜索关键字，NextPageData为分页数据（0获取817以前授权，1获取817以后授权）
        
        Returns:
          transport 解包后的 data（通常为 dict）。
        """
        return await self._t.post('/User/GetUserAuthList', json=body, params=None, timeout=timeout)

    async def user_query_app(self, body: dict[str, Any], *, timeout: Optional[float] = None) -> Any:
        """
        搜索已授权的APP
        
        搜索用户已授权的微信APP
        
        路径: 见本函数内 self._t.post 的第一个参数（与 swagger paths 一致）。
        鉴权: 依赖客户端已设置 wxid（请求头 X-Wxid 由传输层自动附加）。
        
        请求体 JSON:
          查询参数：Appid为APP的AppID
        
        Returns:
          transport 解包后的 data（通常为 dict）。
        """
        return await self._t.post('/User/QueryApp', json=body, params=None, timeout=timeout)

    async def user_subscribe_msg(self, body: dict[str, Any], *, timeout: Optional[float] = None) -> Any:
        """
        订阅消息授权
        
        获取小程序订阅消息授权信息
        
        路径: 见本函数内 self._t.post 的第一个参数（与 swagger paths 一致）。
        鉴权: 依赖客户端已设置 wxid（请求头 X-Wxid 由传输层自动附加）。
        
        请求体 JSON:
          查询参数：Appid为小程序AppID
        
        Returns:
          transport 解包后的 data（通常为 dict）。
        """
        return await self._t.post('/User/SubscribeMsg', json=body, params=None, timeout=timeout)

    async def user_wxa_app_get_auth_info(self, body: dict[str, Any], *, timeout: Optional[float] = None) -> Any:
        """
        获取小程序授权信息
        
        获取指定微信小程序的授权信息
        
        路径: 见本函数内 self._t.post 的第一个参数（与 swagger paths 一致）。
        鉴权: 依赖客户端已设置 wxid（请求头 X-Wxid 由传输层自动附加）。
        
        请求体 JSON:
          查询参数：Appid为小程序AppID
        
        Returns:
          transport 解包后的 data（通常为 dict）。
        """
        return await self._t.post('/User/WxaAppGetAuthInfo', json=body, params=None, timeout=timeout)


class WxAppApi:
    """本组接口与 Swagger 中对应 Tag 一致，各方法含中文说明。"""

    def __init__(self, transport: AsyncHTTPTransport) -> None:
        self._t = transport

    async def wx_app_jslogin(self, body: dict[str, Any], *, timeout: Optional[float] = None) -> Any:
        """
        授权小程序
        
        授权微信小程序并返回授权后的code
        
        路径: 见本函数内 self._t.post 的第一个参数（与 swagger paths 一致）。
        鉴权: 依赖客户端已设置 wxid（请求头 X-Wxid 由传输层自动附加）。
        
        请求体 JSON:
          授权参数：Appid为小程序AppID
        
        Returns:
          transport 解包后的 data（通常为 dict）。
        """
        return await self._t.post('/WxApp/JSLogin', json=body, params=None, timeout=timeout)

    async def wx_app_jsoperate_wx_data(self, body: dict[str, Any], *, timeout: Optional[float] = None) -> Any:
        """
        小程序操作
        
        执行微信小程序的相关操作
        
        路径: 见本函数内 self._t.post 的第一个参数（与 swagger paths 一致）。
        鉴权: 依赖客户端已设置 wxid（请求头 X-Wxid 由传输层自动附加）。
        
        请求体 JSON:
          操作参数：Appid为小程序AppID，Data为操作数据，Opt为操作类型
        
        Returns:
          transport 解包后的 data（通常为 dict）。
        """
        return await self._t.post('/WxApp/JSOperateWxData', json=body, params=None, timeout=timeout)

    async def wx_app_search_suggestion(self, body: dict[str, Any], *, timeout: Optional[float] = None) -> Any:
        """
        获取搜索建议
        
        获取微信小程序的文章搜索建议
        
        路径: 见本函数内 self._t.post 的第一个参数（与 swagger paths 一致）。
        鉴权: 依赖客户端已设置 wxid（请求头 X-Wxid 由传输层自动附加）。
        
        请求体 JSON:
          搜索参数：Keys为搜索关键字
        
        Returns:
          transport 解包后的 data（通常为 dict）。
        """
        return await self._t.post('/WxApp/SearchSuggestion', json=body, params=None, timeout=timeout)

    async def wx_app_web_search(self, body: dict[str, Any], *, timeout: Optional[float] = None) -> Any:
        """
        搜索文章
        
        在微信小程序中搜索文章
        
        路径: 见本函数内 self._t.post 的第一个参数（与 swagger paths 一致）。
        鉴权: 依赖客户端已设置 wxid（请求头 X-Wxid 由传输层自动附加）。
        
        请求体 JSON:
          搜索参数：Keys为搜索关键字，OffSet为分页偏移量，SuggestionID为建议ID
        
        Returns:
          transport 解包后的 data（通常为 dict）。
        """
        return await self._t.post('/WxApp/WebSearch', json=body, params=None, timeout=timeout)


class GeneratedApis:
    """
    聚合 swagger 中全部 POST 接口；按业务标签分子客户端。

    不挂在 LwApiClient 上，避免与 login/msg 等领域客户端重复。
    用法示例::

        rest = GeneratedApis(client.transport)
        await rest.friend.friend_search(body={...})
    """

    def __init__(self, transport: AsyncHTTPTransport) -> None:
        self.favor = FavorApi(transport)
        self.finder = FinderApi(transport)
        self.friend = FriendApi(transport)
        self.group = GroupApi(transport)
        self.label = LabelApi(transport)
        self.login = LoginApi(transport)
        self.mmsns = MmSnsApi(transport)
        self.msg = MsgApi(transport)
        self.official = OfficialApi(transport)
        self.other = OtherApi(transport)
        self.user = UserApi(transport)
        self.wxapp = WxAppApi(transport)

