# example.py
from lwapi import LwApiClient
from lwapi.models.login import ProxyInfo

import qrcode
import asyncio


def generate_colored_qr(data):
    """
    生成带有自定义颜色的二维码
    """
    qr = qrcode.QRCode(
        version=1,  # 控制二维码的大小
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=8,  # 控制二维码字符的大小
        border=1,  # 边框大小
    )

    qr.add_data(data)
    qr.make(fit=True)

    # 打印ASCII字符形式的二维码
    qr.print_ascii()


async def main():
    # 创建 SDK 客户端实例，设置基础 URL
    client = LwApiClient(base_url="http://localhost:8081")

    # # 设置设备 ID 和代理（可选）
    # device_id = "57626334653430613863303265333431"  # 假设设备ID是 device123
    # # proxy = ProxyInfo(host="proxy.example.com", port=8080, type=1)  # 代理信息（如果有）

    # # 获取二维码（用户扫码后登录）
    # print("正在获取二维码...")
    # qr_data = await client.login.get_qr_code(device_id=device_id, proxy=None)
    # # 使用 qr_data 获取二维码信息
    # print(f"二维码的 URL: {qr_data.qr_url}")
    # # print(f"二维码的 Base64 编码: {qr_data.qr_code}")
    # # print(f"二维码过期时间: {qr_data.expired_time} 秒")
    # generate_colored_qr("http://weixin.qq.com/x/" + qr_data.uuid)
    # print(f"下次同一账号登录请用此设备id: {qr_data.device_id}")
    # print(f"Uuid: {qr_data.uuid}")

    # # 根据uuid去定时检测二维码的扫码状态
    # qruuid = qr_data.uuid

    # # 调用 check_qr_code 方法检查二维码扫码状态
    # wxid = await client.login.check_qr_code(uuid=qruuid)
    
    wxid = "wxid_4b9a1yqz3s0322"

    if wxid:
        print(f"登录成功 wxid: {wxid}")
        # 设置 wxid 使后续请求带上该 wxid
        client.transport._config.set_wxid(wxid)
    else:
        print("登录失败~")
        return


    asyncio.create_task(client.login.send_heartbeat(interval=20))

    # 保持程序运行，直到某个事件发生（例如手动停止调试）
    try:
        # 等待直到收到退出信号
        await asyncio.Event().wait()
    except asyncio.CancelledError:
        # 捕获异步任务取消错误，优雅退出
        print("程序被取消，正在清理并退出...")
    except KeyboardInterrupt:
        # 捕获 Ctrl+C 中断程序
        print("收到退出信号，正在停止程序...")

if __name__ == "__main__":
    asyncio.run(main())
