# final_simple_multi_bot.py
import asyncio
import json
from pathlib import Path
from lwapi import LwApiClient
from loguru import logger
import qrcode
from lwapi.models.login import ProxyInfo
from typing import Dict
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



# ==================== 全局管理器 ====================
ACTIVE_BOTS: Dict[str, LwApiClient] = {}
BOT_LOCKS = asyncio.Lock()  # 防止并发写冲突（极少情况）




# ==================== 统一的强大消息回调 ====================
async def on_new_message(client: LwApiClient, resp: SyncMessageResponse):
    """所有账号共用这一个回调，自动区分是谁的消息"""
    wxid = getattr(client.transport._config, "x_wxid", "unknown")
    for msg in resp.addMsgs:
        sender = msg.fromUserName.string or "unknown"
        content = msg.content.string or ""
        time_str = datetime.fromtimestamp(msg.createTime).strftime("%m-%d %H:%M:%S")

        print(f"[{time_str} {wxid} 收到消息] {sender} → {content}")

        # ==================== 这里写你的智能逻辑 ====================
        if "你好" in content:
            await client.msg.send_text_message(to_wxid=sender, content="你好！我是机器人~")

        elif content == "在吗":
            await client.msg.send_text_message(to_wxid=sender, content="在的！有啥事？")

        # 可以继续加：拉群、踢人、发图、改群名、点赞、转发等...


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
           
            # 注册到全局管理器（Web 面板就是通过这里找你的）
            async with BOT_LOCKS:
                    ACTIVE_BOTS[saved_wxid] = client

            logger.success(f"机器人上线 → {remark} | {saved_wxid or '未登录'}")
            
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
             # 清理：避免僵尸 client
            async with BOT_LOCKS:
                ACTIVE_BOTS.pop(saved_wxid, None)

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
