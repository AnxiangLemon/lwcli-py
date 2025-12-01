# final_simple_multi_bot.py
import asyncio
import json
from pathlib import Path
from lwapi import LwApiClient
from loguru import logger
import qrcode
from lwapi.models.login import ProxyInfo

from datetime import datetime
from lwapi.models.msg import SyncMessageResponse
def generate_colored_qr(data):
    """
    生成二维码
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
    qr.print_ascii(invert=True)

# ==================== 配置文件 ====================
CONFIG_FILE = Path("accounts.json")

# 如果没有配置文件，就创建示例
if not CONFIG_FILE.exists():
    example = [
        {
            "device_id": "57626334653430613863303265333431",
            "wxid": "wxid_4b9a1yqz3s0322",           # 第一次留空，扫码后自动填充
            "remark": "主号",
            "proxy": None   # 可以改成 {"host": "127.0.0.1", "port": 1080, "type": 1}

        }
    ]
    CONFIG_FILE.write_text(json.dumps(example, indent=2, ensure_ascii=False))
    print("已创建 accounts.json，请填写 device_id，第一次运行会要二维码")
    exit()

ACCOUNTS = json.loads(CONFIG_FILE.read_text())
BASE_URL = "http://localhost:8081"



# ========== 第一步：定义你的消息处理函数 ==========
async def on_new_message(resp: SyncMessageResponse):
    """每当收到新消息，就会自动调用这个函数"""
    for msg in resp.addMsgs:
        sender = msg.fromUserName.string or "未知用户"
        content = msg.content.string or ""
        time_str = datetime.fromtimestamp(msg.createTime).strftime("%Y-%m-%d %H:%M:%S")

        print("\n" + "="*50)
        print(f"新消息 [{time_str}]")
        print(f"发信人: {sender}")
        print(f"内容: {content}")
        if msg.pushContent:
            print(f"通知栏: {msg.pushContent}")
        print("="*50)

        # 在这里写你的业务逻辑！
        # 比如：
        # if "你好" in content:
        #     await send_text(to_wxid=sender, text="你好！我是机器人")
        # 或存数据库、发钉钉、触发 webhook 等


async def run_one_bot(acc: dict):
    device_id = acc["device_id"]
    remark = acc.get("remark", device_id[:8])
    saved_wxid = acc.get("wxid", "").strip()
    proxy_dict = acc.get("proxy")  # 可能是 None 或 dict
    proxy = ProxyInfo(**proxy_dict) if proxy_dict else None
    
    while True:
        async with LwApiClient(base_url=BASE_URL) as client:
            login = client.login
            login_success = False  # 关键标志位！

            # 调试业务接口
            client.transport._config.set_wxid(saved_wxid)
           # data = await client.msg.sync()
           
            client.msg.start(handler=on_new_message)
            while True:                          # ← 主线程睡大觉
                await asyncio.sleep(60)
            
            try:
                # 情况1：已经有 wxid → 直接二次登录（最快
                if saved_wxid:
                    client.transport._config.set_wxid(saved_wxid)
                    if await login.sec_auto_login():
                        logger.success(f"【{remark}】二次登录成功 → {saved_wxid}")
                        login_success = True
                    else:
                        logger.warning(f"【{remark}】二次登录失败，尝试扫二维码")
                        saved_wxid = ""  # 失效，强制走扫码
                        client.transport.config.set_wxid("")  # 清空

                # 情况2：没有 wxid 或二次失败 → 只能扫二维码
                if not saved_wxid:
                    qr = await login.get_qr_code(device_id, proxy)
                    print(f"【{remark}】请扫码登录 → {qr.qr_url}")
                    generate_colored_qr("http://weixin.qq.com/x/" + qr.uuid)
                    wxid = await login.check_qr_code(qr.uuid, timeout=300)

                    # 登录成功！保存 wxid 到手 → 永久保存
                    saved_wxid = wxid
                    acc["wxid"] = wxid
                    CONFIG_FILE.write_text(json.dumps(ACCOUNTS, indent=2, ensure_ascii=False))
                    client.transport._config.set_wxid(saved_wxid)
                    logger.success(f"【{remark}】二维码登录成功，已保存 wxid: {wxid}")
                    login_success = True

                # 3. 只有真正登录成功，才允许开启心跳！！
                if login_success:
                    login.start_heartbeat(interval=20)
                    logger.info(f"【{remark}】心跳已启动，进入主业务循环")

                    # ==================== 你的业务主循环 ====================
                    while True:
                        await asyncio.sleep(60)
                    # =======================================================
                else:
                    logger.error(f"【{remark}】登录完全失败，本轮不开启心跳，10秒后重试")
                    await asyncio.sleep(10)

            except asyncio.CancelledError:
                logger.info(f"【{remark}】停止运行")
                break
            except Exception as e:
                logger.error(f"【{remark}】出错: {e}，10秒后重连")
                await asyncio.sleep(10)


async def main():
    logger.remove()
    logger.add(lambda msg: print(msg, end=""), colorize=True, level="DEBUG")

    print(f"正在启动 {len(ACCOUNTS)} 个微信账号...")
    tasks = [
        asyncio.create_task(run_one_bot(acc), name=f"Bot-{acc.get('remark','unknown')}")
        for acc in ACCOUNTS
    ]

    try:
        await asyncio.gather(*tasks)
    except KeyboardInterrupt:
        logger.info("\n\nCtrl+C 按下，用户主动退出")
    finally:
        logger.info("正在关闭所有账号...")
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        logger.success("全部账号已安全退出，下次运行自动秒登")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        # 优雅静默退出
        print("\n程序已完全退出，所有资源已释放")
    except Exception as e:
        # 防止意外崩溃
        logger.exception(f"程序异常崩溃: {e}")
# async def main():
#     # 创建 SDK 客户端实例，设置基础 URL
#     client = LwApiClient(base_url="http://localhost:8081")
      #     client2 = LwApiClient(base_url="http://localhost:8081")
#     # 设置设备 ID 和代理（可选）
#     device_id = "57626334653430613863303265333431"  # 假设设备ID是 device123
#     # proxy = ProxyInfo(host="proxy.example.com", port=8080, type=1)  # 代理信息（如果有）

#     # 获取二维码（用户扫码后登录）
#     print("正在获取二维码...")
#     qr_data = await client.login.get_qr_code(device_id=device_id, proxy=None)
#     # 使用 qr_data 获取二维码信息
#     print(f"二维码的 URL: {qr_data.qr_url}")
#     # print(f"二维码的 Base64 编码: {qr_data.qr_code}")
#     # print(f"二维码过期时间: {qr_data.expired_time} 秒")
#     generate_colored_qr("http://weixin.qq.com/x/" + qr_data.uuid)
#     print(f"下次同一账号登录请用此设备id: {qr_data.device_id}")
#     print(f"Uuid: {qr_data.uuid}")

#     # 根据uuid去定时检测二维码的扫码状态
#     qruuid = qr_data.uuid

#     # 调用 check_qr_code 方法检查二维码扫码状态
#     wxid = await client.login.check_qr_code(uuid=qruuid)
    
#     wxid = "wxid_4b9a1yqz3s0322"

#     if wxid:
#         print(f"登录成功 wxid: {wxid}")
#         # 设置 wxid 使后续请求带上该 wxid
#         client.transport._config.set_wxid(wxid)
#     else:
#         print("登录失败~")
#         return


#     asyncio.create_task(client.login.send_heartbeat(interval=20))

#     # 保持程序运行，直到某个事件发生（例如手动停止调试）
#     try:
#         # 等待直到收到退出信号
#         await asyncio.Event().wait()
#     except asyncio.CancelledError:
#         # 捕获异步任务取消错误，优雅退出
#         print("程序被取消，正在清理并退出...")
#     except KeyboardInterrupt:
#         # 捕获 Ctrl+C 中断程序
#         print("收到退出信号，正在停止程序...")

