# lwapi/apis/msg.py
import asyncio
import httpx
from loguru import logger

from ..transport import AsyncHTTPTransport
from ..models.msg import SyncMessageResponse
from .utils import api_call, ApiResponse  # 关键！导入 ApiResponse

from typing import Callable, Optional, Awaitable

MessageHandler = Callable[[SyncMessageResponse], Awaitable[None]]


class MsgClient:
    def __init__(
        self,
        transport: AsyncHTTPTransport,
    ):
        self.t = transport
        self._task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()
        self._handler: Optional[MessageHandler] = None
        self.interval = 1.0

    async def _sync_once(self) -> SyncMessageResponse: 
        """必须明确返回 SyncMessageResponse，装饰器才能正确解析"""
        resp = await self.t.post("/Msg/Sync")
        return SyncMessageResponse.model_validate(resp.data)

    async def _polling_loop(self):
        logger.success("微信消息长轮询已启动")

        while not self._stop_event.is_set():
            try:
                #: ApiResponse[SyncMessageResponse] 
                resp= await self._sync_once()

                if resp and resp.addMsgs:
                    logger.info(f"收到 {len(resp.addMsgs)} 条新消息")
                    if self._handler:
                        await self._handler(resp)   # 传的是真正的 SyncMessageResponse 对象

                await asyncio.sleep(self.interval)

            except httpx.ReadTimeout:
                # 忽略 ReadTimeout 异常，继续下次轮询
                await asyncio.sleep(self.interval)  # 等待一段时间后继续轮询
            except asyncio.CancelledError:
                break
            except Exception as e:
                #logger.exception(f"消息轮询异常: {e}")
                await asyncio.sleep(2)

        logger.info("消息轮询已停止")

    def start(self, handler: MessageHandler):
        """一行启动轮询！"""
        if self._task and not self._task.done():
            logger.warning("轮询已启动，请勿重复启动")
            return
        self._handler = handler
        self._stop_event.clear()
        self._task = asyncio.create_task(self._polling_loop())
        logger.success("消息轮询启动成功")

    def stop(self):
        """停止轮询"""
        self._stop_event.set()
        if self._task:
            self._task.cancel()

    async def wait_stop(self):
        """等待轮询彻底结束（用于程序退出）"""
        if self._task:
            await self._task
