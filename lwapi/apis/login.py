# lwapi/apis/login.py
import time
from typing import Optional
from ..transport import SyncHTTPTransport
from ..models.login import QRGetRequest, QRGetResponse, ProxyInfo
from ..models.login import QRCheckResponse
from ..models.base import ResponseResult


class LoginClient:
    def __init__(self, transport: SyncHTTPTransport):
        """初始化登录客户端"""
        self._transport = transport

    def get_qr_code(
        self, device_id: str, proxy: Optional[ProxyInfo] = None
    ) -> QRGetResponse:
        """
        获取登录二维码
        :param device_id: 设备ID
        :param proxy: 代理信息（可选）
        :return: 返回包含二维码信息的 QRGetResponse 对象
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
            return qr_data  # 直接返回 QRGetResponse 对象
        else:
            raise Exception(f"获取二维码失败: {result.message}")

    def check_qr_code(
        self, uuid: str, interval: int = 5, max_retries: int = 60
    ) -> Optional[str]:
        """
        根据 UUID 定时检查二维码扫码状态
        :param uuid: 二维码的 UUID
        :param interval: 检查间隔时间，单位秒，默认 5 秒
        :param max_retries: 最大重试次数
        :return:
        """
        retries = 0
        while retries < max_retries:
            # 调用 /Login/QRCheck 接口检查二维码状态
            result: ResponseResult[dict] = self._transport.post(
                "/Login/QRCheck?uuid="+uuid
            )

          
            if result.RetCode == 200:
            #   qr_check_data = QRCheckResponse.parse_obj(result.data)
                print(f"检查二维码状态: {result.data}")
            else:
                print(f"检查二维码状态失败: {result.message}")

            retries += 1
            print(f"等待 {interval} 秒后重新检查...")
            time.sleep(interval)  # 等待指定的时间后重新检查

        print("二维码扫码超时！")
        return None
