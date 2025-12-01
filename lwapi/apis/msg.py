# lwapi/apis/msg.py
from __future__ import annotations   # ← 第1行：Python 3.7+ 推荐，必须加！

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..client import LwApiClient  # ← 第2行：只在类型检查时导入，运行时不执行
else:
    # 运行时用字符串，避免循环导入
    LwApiClient = None  # type: ignore  # ← 第3行：骗过 Ruff

import asyncio
import httpx
from loguru import logger
from typing import Callable, Awaitable, Optional

# 导入根客户端类型（前向声明也可以，但这里直接导入更清晰）
from ..transport import AsyncHTTPTransport
from ..models.msg import SyncMessageResponse


# ==================== 新版回调类型：直接传入完整的 LwApiClient ====================
# 现在你的回调函数签名是：
# async def on_message(client: LwApiClient, resp: SyncMessageResponse)
MessageHandler = Callable[["LwApiClient", SyncMessageResponse], Awaitable[None]]


class MsgClient:
    def __init__(self, transport: AsyncHTTPTransport):
        self.t = transport
        
        # 【关键修改1】添加 client 反向引用，由 LwApiClient.__init__ 注入
        # 这样我们就能在回调里拿到完整的 client 实例（发消息、拉群、发朋友圈...）
        self.client: "LwApiClient | None" = None   # ← 改成字符串

        self._task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()
        self._handler: Optional[MessageHandler] = None
        self.interval = 1.0  # 轮询间隔（秒）

    async def _sync_once(self) -> SyncMessageResponse:
        """单次同步消息"""
        data = await self.t.post("/Msg/Sync")
        return SyncMessageResponse.model_validate(data)

    async def _polling_loop(self):
        logger.success("微信消息长轮询已启动")

        while not self._stop_event.is_set():
            try:
                resp = await self._sync_once()

                if resp.addMsgs:
                    logger.info(f"收到 {len(resp.addMsgs)} 条新消息")
                    
                    # 【关键修改2】不再直接调用 handler(resp)
                    # 而是调用 handler(self.client, resp) —— 注入完整的 client 实例！
                    if self._handler and self.client:
                        try:
                            await self._handler(self.client, resp)
                        except Exception as e:
                            logger.error(f"消息处理函数异常: {e}", exc_info=True)
                    elif not self.client:
                        logger.error("MsgClient.client 未注入！无法调用消息处理器")

                await asyncio.sleep(self.interval)

            except httpx.ReadTimeout:
                # 长轮询超时是正常现象，继续下一次
                await asyncio.sleep(self.interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"消息轮询异常: {e}")
                await asyncio.sleep(2)

        logger.info("消息轮询已停止")

    # ==================== 启动监听 ====================
    def start(self, handler: MessageHandler):
        """启动消息监听，回调会收到完整的 LwApiClient 实例"""
        if self._task and not self._task.done():
            logger.warning("消息轮询已启动，请勿重复启动")
            return

        if not self.client:
            logger.error("MsgClient.client 未设置！请确保在 LwApiClient 中注入了 self.msg.client = self")
            return

        self._handler = handler
        self._stop_event.clear()
        self._task = asyncio.create_task(self._polling_loop())
        logger.success("消息长轮询启动成功")

    # ==================== 停止监听 ====================
    def stop(self):
        """停止消息轮询"""
        self._stop_event.set()
        if self._task:
            self._task.cancel()

    async def wait_stop(self):
        """等待轮询任务彻底结束（优雅退出时使用）"""
        if self._task:
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            
            
    async def send_text_message(
        self,
        to_wxid: str,
        content: str,
        at: Optional[str] = None,
    ) -> dict:
        """
        发送文本消息（支持单聊、群聊、@成员）

        Args:
            to_wxid: 接收者 wxid（个人）或群ID（群聊，如 xxx@chatroom）
            content: 消息内容
            at: 群聊时要@的人，多个用英文逗号分隔（如：wxid_abc,wxid_def）
                如果不需要@，传 None 或空字符串

        Returns:
            dict: 原始返回结果，包含 code, data, message
        """
        payload = {
            "to_wxid": to_wxid,
            "content": content,
        }
        if at is not None:
            payload["at"] = at.strip()

        data = await self.t.post("/Msg/SendTxt", json=payload)
        
        # 统一返回原始结构，便于你判断成功失败
        return data
    