# lwapi/models/msg_requests.py
"""
与 swagger `definitions` 中 msg.* 请求体对齐的模型，用于生成发给 /Msg/* 的 JSON。

插件里请用「Python 字段名 + 类型提示」，再调用 ``.to_api()`` 得到服务端需要的 camelCase 字典，
避免手写 ``{"toWxid": ...}`` 时拼错键名。

发文本请优先使用 :meth:`lwapi.apis.msg.MsgClient.send_text_message`；若已持有
:class:`SendNewMsgParam` 实例，可调用 :meth:`~lwapi.apis.msg.MsgClient.send_text_body`。

示例::

    from lwapi import SendNewMsgParam

    await client.msg.send_text_message(to_wxid=sender, content="你好")
    await client.msg.send_text_body(SendNewMsgParam(to_wxid=sender, content="你好"))
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import Field

from . import BaseModelWithConfig


class MsgRequestBody(BaseModelWithConfig):
    """msg 类请求体基类：输出与 LwApi 文档一致的 JSON 键名。"""

    def to_api(self) -> dict[str, Any]:
        return self.model_dump(mode="json", by_alias=True, exclude_none=True)


class SendNewMsgParam(MsgRequestBody):
    """swagger: msg.SendNewMsgParam，对应 POST /Msg/SendTxt（发文本）。"""

    to_wxid: str = Field(..., serialization_alias="toWxid", description="接收者 wxid 或群 chatroom id")
    content: str = Field(..., description="消息正文")
    at: Optional[str] = Field(
        None,
        description="群聊 @ 成员，多个 wxid 用英文逗号分隔；不需要 @ 时不要传或传 None",
    )


class SendImageMsgParam(MsgRequestBody):
    """swagger: msg.SendImageMsgParam，对应 POST /Msg/UploadImg。"""

    to_wxid: str = Field(..., serialization_alias="toWxid", description="接收者 wxid 或群 id")
    image_b64: str = Field(
        ...,
        serialization_alias="base64",
        description="图片二进制经 Base64 编码后的字符串（对应 JSON 键 base64）",
    )


class SendAppMsgParam(MsgRequestBody):
    """swagger: msg.SendAppMsgParam，对应 POST /Msg/SendApp。"""

    to_wxid: str = Field(..., serialization_alias="toWxid", description="接收者 wxid")
    xml: str = Field(..., description="小程序 XML 数据")
    msg_type: int = Field(
        ...,
        serialization_alias="type",
        description="小程序消息类型（与业务场景一致，对应 swagger 字段 type）",
    )


class SendVideoMsgParam(MsgRequestBody):
    """swagger: msg.SendVideoMsgParam，对应 POST /Msg/SendVideo。"""

    to_wxid: str = Field(..., serialization_alias="toWxid", description="接收者 wxid")
    play_length: int = Field(..., serialization_alias="playLength", description="视频时长（秒）")
    video_b64: str = Field(
        ...,
        serialization_alias="base64",
        description="视频内容 Base64（对应 JSON 键 base64）",
    )
    image_base64: str = Field(..., serialization_alias="imageBase64", description="封面图 Base64")


class SendShareLinkMsgParam(MsgRequestBody):
    """swagger: msg.SendShareLinkMsgParam，对应 POST /Msg/ShareLink。"""

    to_wxid: str = Field(..., serialization_alias="toWxid", description="接收者 wxid")
    title: str = Field(..., description="链接标题")
    desc: str = Field(..., description="链接描述")
    url: str = Field(..., description="链接 URL")
    thumb_url: str = Field(..., serialization_alias="thumbUrl", description="缩略图 URL")


class RevokeMsgParam(MsgRequestBody):
    """swagger: msg.RevokeMsgParam，对应 POST /Msg/Revoke；字段按实际撤回场景选填。"""

    client_msg_id: Optional[int] = Field(None, serialization_alias="clientMsgId")
    create_time: Optional[int] = Field(None, serialization_alias="createTime")
    new_msg_id: Optional[int] = Field(None, serialization_alias="newMsgId")
    to_user_name: Optional[str] = Field(None, serialization_alias="toUserName")
    wxid: Optional[str] = Field(None, description="相关 wxid，视服务端要求填写")
