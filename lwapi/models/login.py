# models/login.py
from pydantic import BaseModel, Field
from typing import Optional
from .base import alias_generator  # 导入 base.py 中的 alias_generator


class ProxyInfo(BaseModel):
    """代理信息，留空表示不使用代理"""
    host: Optional[str] = None
    port: Optional[int] = None
    type: Optional[int] = None  # 代理类型，0：无，1：http，2：https，3：socks5

class QRGetRequest(BaseModel):
    """用于获取微信登录二维码的请求体"""
    deviceId: str = Field(..., description="设备ID，用于标识登录设备")
    osType: int = Field(0, description="操作系统类型，默认为0（未知系统）")
    proxy: Optional[ProxyInfo] = None  # 代理信息，留空表示不使用代理

class QRGetResponse(BaseModel):
    """二维码获取响应体"""
    qr_code: str = Field(..., alias="QrBase64", description="二维码的 Base64 图像")
    qr_url: str = Field(..., alias="QrUrl", description="二维码的 URL")
    expired_time: int = Field(..., alias="ExpiredTime", description="二维码的过期时间（秒）")
    device_id: str = Field(..., alias="DeviceId", description="设备 ID")
    uuid: str = Field(..., alias="Uuid", description="二维码 ID")
    
    class Config:
        # 允许字段使用别名
        validate_by_name  = True
        # 设置别名转换
        alias_generator = alias_generator
       
class QRCheckResponse(BaseModel):
    """扫码状态检查响应体"""
    status: Optional[int] = Field(None, description="二维码的状态")
    expiredTime: Optional[int] = Field(None, description="二维码的过期时间（秒）")

    class Config:
        # 配置为允许字段缺失或为None
        extra = "allow"  # 允许接收未定义的字