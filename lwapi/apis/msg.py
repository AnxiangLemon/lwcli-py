# lwapi/apis/msg.py
from __future__ import annotations   # ← 第1行：Python 3.7+ 推荐，必须加！

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..client import LwApiClient

import aiohttp
import base64
import asyncio
import httpx
from loguru import logger
from typing import Callable, Awaitable, Optional

# 导入根客户端类型（前向声明也可以，但这里直接导入更清晰）
from ..exceptions import HttpError, is_wrapped_request_timeout
from ..transport import AsyncHTTPTransport
from ..models.msg import SyncMessageResponse
from ..models.msg_requests import SendImageMsgParam, SendNewMsgParam

MessageHandler = Callable[["LwApiClient", SyncMessageResponse], Awaitable[None]]


class MsgClient:
    def __init__(self, transport: AsyncHTTPTransport):
        self.t = transport
        
        # 由 LwApiClient 在初始化时注入，便于回调中直接调用完整 SDK 能力。
        self.client: "LwApiClient | None" = None

        self._task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()
        self._handler: Optional[MessageHandler] = None
        self.interval = 1.0  # 轮询间隔（秒）

    async def _sync_once(self) -> SyncMessageResponse:
        """单次同步消息（服务端长轮询，超时需明显长于普通接口）。"""
        data = await self.t.post("/Msg/Sync", timeout=180.0)
        return SyncMessageResponse.model_validate(data)

    async def _polling_loop(self):
        logger.success("微信消息长轮询已启动")

        while not self._stop_event.is_set():
            try:
                resp = await self._sync_once()

                if resp.addMsgs:
                    logger.info(f"收到 {len(resp.addMsgs)} 条新消息")
                    
                    # 统一向回调注入 client，处理器里可以直接调发消息等接口。
                    if self._handler and self.client:
                        try:
                            await self._handler(self.client, resp)
                        except Exception:
                            logger.exception("消息处理函数异常")
                    elif not self.client:
                        logger.error("MsgClient.client 未注入！无法调用消息处理器")

                await asyncio.sleep(self.interval)

            except httpx.TimeoutException:
                await asyncio.sleep(self.interval)
            except HttpError as e:
                if is_wrapped_request_timeout(e):
                    await asyncio.sleep(self.interval)
                    continue
                logger.warning(f"消息轮询异常: {e}")
                await asyncio.sleep(2)
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
        发送文本消息（支持单聊、群聊、@成员）。

        内部使用 :class:`~lwapi.models.msg_requests.SendNewMsgParam` 生成 JSON，避免手写 dict 键名错误。
        需要「已构造好的请求体」时可用 :meth:`send_text_body`。

        Args:
            to_wxid: 接收者 wxid（个人）或群ID（群聊，如 xxx@chatroom）
            content: 消息内容
            at: 群聊时要@的人，多个用英文逗号分隔（如：wxid_abc,wxid_def）
                如果不需要@，传 None 或空字符串

        Returns:
            dict: 原始返回结果，包含 code, data, message
        """
        at_clean = at.strip() if at and at.strip() else None
        payload = SendNewMsgParam(
            to_wxid=to_wxid,
            content=content,
            at=at_clean,
        ).to_api()

        data = await self.t.post("/Msg/SendTxt", json=payload)

        # 统一返回原始结构，便于你判断成功失败
        return data


    async def send_image_by_url(
        self,
        to_wxid: str,
        image_url: str,
        timeout: int = 30,
    ) -> dict:
        """
        发送图片消息（支持传入图片 URL，自动下载并转 Base64）

        Args:
            to_wxid: 接收者 wxid（个人）或群ID（群聊，如 xxx@chatroom）
            image_url: 图片的直链 URL（支持 jpg/png/gif/webp 等常见格式）
            timeout: 下载超时时间（秒），默认 30 秒

        Returns:
            dict: 原始返回结果，包含 code, data, message
                  成功时 data 中通常有 msg_id 等信息

        Raises:
            ValueError: 下载失败或图片过大
            aiohttp.ClientError: 网络异常
        """
        # Step 1: 下载图片并转为 Base64
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
                async with session.get(image_url) as resp:
                    if resp.status != 200:
                        raise ValueError(f"图片下载失败，HTTP {resp.status}: {image_url}")
                    
                    image_bytes = await resp.read()
                    
                    # 可选：限制大小（微信单张图片建议 ≤ 10MB）
                    if len(image_bytes) > 5 * 1024 * 1024:
                        raise ValueError(f"图片过大（{len(image_bytes)/1024/1024:.2f}MB），微信限制建议 ≤ 5MB")
                    
                    base64_str = base64.b64encode(image_bytes).decode('utf-8')
        except Exception as e:
            raise ValueError(f"图片下载或编码失败: {str(e)}") from e

        # Step 2: 调用原始发送图片接口
        payload = SendImageMsgParam(to_wxid=to_wxid, image_b64=base64_str).to_api()

        data = await self.t.post("/Msg/UploadImg", json=payload)
        return data
    