# lwapi/models/other_requests.py
"""杂项 / 下载 / CDN（misc.*）请求体。"""

from __future__ import annotations

from typing import Optional

from pydantic import Field

from .json_payload import ApiJsonBody


class MiscSection(ApiJsonBody):
    start_pos: int = Field(..., serialization_alias="startPos", description="起始位置")
    data_len: int = Field(..., serialization_alias="dataLen", description="数据长度")


class MiscCdnDownloadImageParam(ApiJsonBody):
    file_no: str = Field(..., serialization_alias="fileNo", description="文件编号")
    file_aes_key: str = Field(..., serialization_alias="fileAesKey", description="AES 密钥")


class MiscDownloadAppAttachParam(ApiJsonBody):
    app_id: str = Field(..., serialization_alias="appId", description="应用 ID")
    attach_id: str = Field(..., serialization_alias="attachId", description="附件 ID")
    user_name: str = Field(..., serialization_alias="userName", description="发送者 wxid")
    data_len: int = Field(..., serialization_alias="dataLen", description="文件大小")
    section: MiscSection = Field(..., description="下载段")


class MiscDownloadParam(ApiJsonBody):
    to_wxid: str = Field(..., serialization_alias="toWxid", description="目标 wxid")
    msg_id: int = Field(..., serialization_alias="msgId", description="消息 ID")
    data_len: int = Field(..., serialization_alias="dataLen", description="数据长度")
    section: MiscSection = Field(..., description="下载段")
    compress_type: int = Field(0, serialization_alias="compressType", description="压缩类型")


class MiscDownloadVoiceParam(ApiJsonBody):
    bufid: str = Field(..., description="语音 bufid")
    from_user_name: str = Field(..., serialization_alias="fromUserName", description="发送者 wxid")
    length: int = Field(..., description="语音数据长度")
    msg_id: int = Field(..., serialization_alias="msgId", description="消息 ID")


class MiscGetA8KeyParam(ApiJsonBody):
    req_url: str = Field(..., serialization_alias="reqUrl", description="请求 URL")
    scene: int = Field(4, description="场景值")
    op_code: int = Field(2, serialization_alias="opCode", description="操作码")
    code_type: int = Field(19, serialization_alias="codeType")
    code_version: int = Field(5, serialization_alias="codeVersion")
    net_type: str = Field("wifi", serialization_alias="netType")
    cookie_base64: Optional[str] = Field(None, serialization_alias="cookieBase64")
    flag: int = Field(0)


class MiscThirdAppGrantParam(ApiJsonBody):
    appid: str = Field(..., description="第三方应用 ID")
