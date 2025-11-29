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
    qr_code_url = client.login.get_qr_code(device_id=device_id, proxy=None)  # 调用 LoginClient 获取二维码
    print(f"请扫描二维码进行登录：{qr_code_url}")  # 输出二维码 URL，用户可以用手机扫描

    # 等待用户扫码成功后（这个流程需要你根据实际情况处理，比如检查状态）
    input("按回车键继续，确认二维码扫码成功...")


if __name__ == "__main__":
    main()
