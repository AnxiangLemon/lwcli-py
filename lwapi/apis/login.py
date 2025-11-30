# lwapi/apis/login.py
import asyncio
import time
from typing import Optional
from ..transport import AsyncHTTPTransport
from ..models.login import QRGetRequest, QRGetResponse, ProxyInfo
from ..models.login import QRCheckResponse


class LoginClient:
    def __init__(self, transport: AsyncHTTPTransport):
        """初始化登录客户端"""
        self._transport = transport

    async def get_qr_code(
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
        result = await self._transport.post(
            "/Login/QRGet", json=qr_code_request.model_dump()
        )

        if result.RetCode == 200:  # 使用 RetCode 来检查响应码
            # 将返回的字典转换为 QRGetResponse 对象
            qr_data = QRGetResponse.parse_obj(result.data)
            return qr_data  # 直接返回 QRGetResponse 对象
        else:
            raise Exception(f"获取二维码失败: {result.message}")

    async def check_qr_code(
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
            result = await self._transport.post("/Login/QRCheck?uuid=" + uuid)
            print(f"检查二维码状态: {result.data}")
            if result.RetCode == 200:
                qr_check_data = QRCheckResponse.parse_obj(result.data)
         
                # 根据 state 判断二维码的状态
                if qr_check_data.status == 0:
                    # 状态 0：还未扫码
                    print(f"请用手机微信扫描二维码 {qr_check_data.expiredTime}秒")
                elif qr_check_data.status == 1:
                    # 状态 1：扫码成功
                    print(f"请在手机上确定登录 {qr_check_data.expiredTime}秒")
                elif qr_check_data.status == 2:
                    # 状态 2：正在登录
                    print("正在登录...")
                    # 在此可以进行进一步的登录验证或处理
                    return None
                elif qr_check_data.status == 3:
                    # 状态 3：二维码已过期
                    print("二维码已过期")
                    return None  # 返回 None，表示二维码过期
                elif qr_check_data.status == 4:
                    # 状态 4：二维码已取消
                    print("二维码已取消")
                    return None  # 返回 None，表示二维码被取消
                elif qr_check_data.status == -2007:
                    # 状态 -2007：二维码已过期
                    print("二维码已过期")
                    return None  # 返回 None，表示二维码过期
                else:
                    # 其他未知状态
                    print(f"未知状态，状态码：{qr_check_data.status}")
                    return None
            else:
                print(f"检查二维码状态失败: {result.message}")
                return None

            retries += 1
            await asyncio.sleep(interval)  # 异步等待

        print("二维码扫码超时！")
        return None

    async def send_heartbeat(self, interval: int = 60, max_retries: int = 5):
        """
        发送心跳包以保持登录会话活跃
        :param interval: 心跳包发送间隔时间，单位秒，默认 60 秒
        :param max_retries: 最大重试次数
        """
        retries = 0
        while retries < max_retries:
            # 发送心跳包请求
            result = await self._transport.post(
                "/Login/HeartBeat"  # 请求路径
            )

            if result.RetCode != 200:
                print(f"发送心跳包失败: {result.message}")
                retries += 1  # 失败时自增 retries
                
            await asyncio.sleep(interval)  # 等待指定时间后重新发送心跳包

        print(f"已达到最大重试次数，{self._transport._config.x_wxid}停止发送心跳包")
