# example.py
from lwapi import LwApiClient
from lwapi.models.login import ProxyInfo


def main():
    # 创建 SDK 客户端实例，设置基础 URL
    client = LwApiClient(base_url="http://localhost:8081")

    # 设置设备 ID 和代理（可选）
    device_id = "device123"  # 假设设备ID是 device123
    # proxy = ProxyInfo(host="proxy.example.com", port=8080, type=1)  # 代理信息（如果有）

    # 获取二维码（用户扫码后登录）
    print("正在获取二维码...")
    qr_data = client.login.get_qr_code(device_id=device_id, proxy=None)
    # 使用 qr_data 获取二维码信息
    print(f"二维码的 URL: {qr_data.qr_url}")
    # print(f"二维码的 Base64 编码: {qr_data.qr_code}")
    print(f"二维码过期时间: {qr_data.expired_time} 秒")
    print(f"设备 ID: {qr_data.device_id}")
    print(f"Uuid: {qr_data.uuid}") 
    
    #根据uuid去定时检测二维码的扫码状态
    qruuid = qr_data.uuid
    

  # 调用 check_qr_code 方法检查二维码扫码状态
    wxid = client.login.check_qr_code(uuid=qruuid)

    if wxid:
        print(f"成功获取到 wxid: {wxid}")
    else:
        print("二维码扫码失败或已过期，请重新生成二维码！")


if __name__ == "__main__":
    main()
