import qrcode
import http.client
import json


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


conn = http.client.HTTPConnection("103.91.208.68", 8081)
payload = json.dumps(
    {
        "deviceId": "device123",
        "osType": 0,
        "proxy": {"proxyIp": "", "proxyPassword": "", "proxyUser": ""},
    }
)
headers = {"Content-Type": "application/json"}
conn.request("POST", "/api/Login/QRGet", payload, headers)
res = conn.getresponse()
data = res.read()
# 解码响应并将其转换为字典
response_json = json.loads(data.decode("utf-8"))
# print(response_json) ##返回的数据里面 有设备id uuid 二维码图片等等信息
# 提取想要的字段
uuid = response_json["data"]["Uuid"]
generate_colored_qr("http://weixin.qq.com/x/" + uuid)
