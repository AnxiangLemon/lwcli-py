# lwapi/apis/login.py
from typing import Optional
from ..transport import SyncHTTPTransport
from ..models.login import QRGetRequest, QRGetResponse,ProxyInfo
from ..models.base import ResponseResult

class LoginClient:
    def __init__(self, transport: SyncHTTPTransport):
        """初始化登录客户端"""
        self._transport = transport

    def get_qr_code(self, device_id: str, proxy: Optional[ProxyInfo] = None) -> str:
        """
        获取登录二维码
        :param device_id: 设备ID
        :param proxy: 代理信息（可选）
        :return: 返回二维码的 URL
        """
        # 创建 QRGetRequest 请求体
        qr_code_request = QRGetRequest(deviceId=device_id, proxy=proxy)

        # 发送请求，获取二维码
        result: ResponseResult[dict] = self._transport.post(
            "/Login/QRGet", json=qr_code_request.model_dump()
        )

        if result.RetCode == 200:  # 使用 RetCode 来检查响应码
            # 将返回的字典转换为 QRGetResponse 对象
            qr_data = QRGetResponse.parse_obj(result.data)
            
            # 返回二维码的 URL 和其他信息
            qr_code_url = qr_data.qr_url
            print(f"二维码已生成，点击链接或扫描二维码进行登录: {qr_code_url}")
            print(f"二维码图片的 Base64 编码：{qr_data.qr_code}")  # 可以显示 Base64 编码（可选）
            print(f"二维码过期时间：{qr_data.expired_time} 秒")
            print(f"设备 ID：{qr_data.device_id}")
            return qr_code_url
        else:
            raise Exception(f"获取二维码失败: {result.message}")
