# models/login.py
from pydantic import Field, BaseModel, ConfigDict, AliasChoices
from typing import Optional
from ..models import BaseModelWithConfig


class ProxyInfo(BaseModelWithConfig):
    """代理信息，留空表示不使用代理"""
    host: Optional[str] = None
    port: Optional[int] = None
    type: Optional[int] = None  # 代理类型，0：无，1：http，2：https，3：socks5

class QRGetRequest(BaseModelWithConfig):
    """用于获取微信登录二维码的请求体"""
    clientUuid: str = Field(..., description="客户端安装种子，用于派生设备指纹")
    osType: int = Field(0, description="操作系统类型，默认为0（未知系统）")
    proxy: Optional[ProxyInfo] = None  # 代理信息，留空表示不使用代理

class QRGetResponse(BaseModelWithConfig):
    """二维码获取响应体"""
    qr_code: str = Field(..., alias="QrBase64", description="二维码的 Base64 图像")
    qr_url: str = Field(..., alias="QrUrl", description="二维码的 URL")
    expired_time: int = Field(..., alias="ExpiredTime", description="二维码的过期时间（秒）")
    client_uuid: str = Field(
        "",
        validation_alias=AliasChoices("ClientUuid", "clientUuid", "client_uuid"),
        description="客户端安装种子（可回写配置；与 DeviceId 不同）",
    )
    device_id: str = Field(
        "",
        validation_alias=AliasChoices("DeviceId", "deviceId", "device_id"),
        description="服务端派生设备指纹，仅存档，不可用于后续请求",
    )
    uuid: str = Field(..., alias="Uuid", description="二维码 ID")
       
class QRCheckResponse(BaseModel):
    """扫码状态检查响应体"""
    model_config = ConfigDict(extra="allow")  # 继续允许未定义字段

    uuid: Optional[str] = Field(None, description="二维码UUID")
    status: Optional[int] = Field(None, description="二维码状态")
    expiredTime: Optional[int] = Field(None, description="二维码过期时间（秒）")

    nickName: Optional[str] = Field(None, description="扫码人昵称")
    headImgUrl: Optional[str] = Field(None, description="扫码人头像")
    pushLoginUrlexpiredTime: Optional[int] = Field(None, description="推送登录链接过期时间")

    verifyUrl: Optional[str] = Field(None, description="安全验证链接（如 weixin110）")