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

from typing import Optional

from pydantic import Field

from .json_payload import ApiJsonBody


class MsgRequestBody(ApiJsonBody):
    """msg 类请求体基类。"""


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


class MsgForwardXmlParam(MsgRequestBody):
    """swagger: msg.DefaultParam，用于 CDN 转发类接口（Content 为消息 XML）。"""

    to_wxid: str = Field(..., serialization_alias="toWxid", description="接收者 wxid")
    content: str = Field(..., description="消息 XML 内容")


class SendEmojiParam(MsgRequestBody):
    """swagger: msg.SendEmojiParam。"""

    to_wxid: str = Field(..., serialization_alias="toWxid", description="接收者 wxid")
    total_len: int = Field(..., serialization_alias="totalLen", description="表情数据长度")
    md5: str = Field(..., description="表情数据 MD5")


class SendQuoteMsgParam(MsgRequestBody):
    """swagger: msg.SendQuoteMsgParam。"""

    to_wxid: str = Field(..., serialization_alias="toWxid", description="接收者 wxid")
    fromusr: str = Field(..., description="被引用人 wxid")
    displayname: str = Field(..., description="被引用人显示名")
    new_msg_id: str = Field(..., serialization_alias="newMsgId", description="被引用消息 newMsgId")
    msg_content: str = Field(..., serialization_alias="msgContent", description="新消息正文")
    quote_content: str = Field(..., serialization_alias="quoteContent", description="引用展示内容")
    msg_seq: str = Field("0", serialization_alias="msgSeq", description="消息序列号")


class SendVoiceMessageParam(MsgRequestBody):
    """swagger: msg.SendVoiceMessageParam。"""

    to_wxid: str = Field(..., serialization_alias="toWxid", description="接收者 wxid")
    voice_b64: str = Field(..., serialization_alias="base64", description="语音 Base64")
    voice_type: int = Field(..., serialization_alias="type", description="AMR=0, MP3=2, SILK=4, SPEEX=1, WAVE=3")
    voice_time: int = Field(..., serialization_alias="voiceTime", description="时长（毫秒，1000 为一秒）")
    wxid: Optional[str] = Field(None, description="部分场景需要，可留空")


class ShareCardParam(MsgRequestBody):
    """swagger: msg.ShareCardParam。"""

    to_wxid: str = Field(..., serialization_alias="toWxid", description="接收者 wxid")
    card_wx_id: str = Field(..., serialization_alias="cardWxId", description="名片 wxid")
    card_nick_name: str = Field(..., serialization_alias="cardNickName", description="名片昵称")
    card_alias: str = Field("", serialization_alias="cardAlias", description="名片别名")


class ShareLocationParam(MsgRequestBody):
    """swagger: msg.ShareLocationParam。"""

    to_wxid: str = Field(..., serialization_alias="toWxid", description="接收者 wxid")
    x: float = Field(..., description="经度")
    y: float = Field(..., description="纬度")
    scale: float = Field(1.0, description="地图缩放比例")
    label: str = Field("", description="位置标签")
    poiname: str = Field("", description="位置名称")
    infourl: str = Field("", serialization_alias="infourl", description="附加信息 URL")


class ShareVideoXmlParam(MsgRequestBody):
    """swagger: msg.ShareVideoMsgParam（分享视频 XML）。"""

    to_wxid: str = Field(..., serialization_alias="toWxid", description="接收者 wxid")
    xml: str = Field(..., description="视频消息 XML")


class RevokeMsgParam(MsgRequestBody):
    """swagger: msg.RevokeMsgParam，对应 POST /Msg/Revoke；字段按实际撤回场景选填。"""

    client_msg_id: Optional[int] = Field(None, serialization_alias="clientMsgId")
    create_time: Optional[int] = Field(None, serialization_alias="createTime")
    new_msg_id: Optional[int] = Field(None, serialization_alias="newMsgId")
    to_user_name: Optional[str] = Field(None, serialization_alias="toUserName")
    wxid: Optional[str] = Field(None, description="相关 wxid，视服务端要求填写")
