from lwapi import LwApiClient

client = LwApiClient("http://127.0.0.1:9999/api")

# 登录（不带 wxid）
resp = client.login.login("user", "password")
print("登录成功, wxid=", client.session.wxid)

# 后续自动带 wxid
client.msg.send_text("wxid_xxx", "你好，这是一条测试消息")
