# lwapi/apis/msg.py
from __future__ import annotations   # ← 第1行：Python 3.7+ 推荐，必须加！

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..client import LwApiClient

import aiohttp
import base64
import asyncio
import httpx
import json
from loguru import logger
from typing import Callable, Awaitable, Optional, Any

# 导入根客户端类型（前向声明也可以，但这里直接导入更清晰）
from ..exceptions import HttpError, is_wrapped_request_timeout
from ..sync_utils import SyncMode, build_msg_ws_url, normalize_sync_mode
from ..transport import AsyncHTTPTransport
from ..models.base import ApiResponse
from ..models.msg import SyncMessageResponse
from ..models.msg_requests import (
    MsgForwardXmlParam,
    RevokeMsgParam,
    SendAppMsgParam,
    SendEmojiParam,
    SendImageMsgParam,
    SendNewMsgParam,
    SendQuoteMsgParam,
    SendShareLinkMsgParam,
    SendVideoMsgParam,
    SendVoiceMessageParam,
    ShareCardParam,
    ShareLocationParam,
    ShareVideoXmlParam,
)

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
        self._sync_mode: SyncMode = "websocket"
        self._ws_session: Optional[aiohttp.ClientSession] = None

    async def _sync_once(self) -> SyncMessageResponse:
        """单次同步消息（服务端长轮询，超时需明显长于普通接口）。"""
        data = await self.t.post("/Msg/Sync", timeout=180.0)
        return SyncMessageResponse.model_validate(data)

    async def sync_messages(self, *, timeout: float = 180.0) -> SyncMessageResponse:
        """
        主动拉取一次消息同步（长轮询）。

        与内部轮询使用同一接口；一般无需单独调用，除非自建轮询逻辑。
        """
        data = await self.t.post("/Msg/Sync", timeout=timeout)
        return SyncMessageResponse.model_validate(data)

    async def _polling_loop(self):
        logger.success("微信消息长轮询已启动")

        while not self._stop_event.is_set():
            try:
                resp = await self._sync_once()

                if resp.addMsgs:
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

    def _parse_sync_payload(self, raw: str | bytes | dict) -> Optional[SyncMessageResponse]:
        """解析 WebSocket 推送的同步消息体（兼容裸 data 与 ApiResponse 包装）。"""
        if isinstance(raw, (str, bytes)):
            try:
                payload = json.loads(raw)
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                logger.warning(f"WebSocket 消息非 JSON: {e}")
                return None
        elif isinstance(raw, dict):
            payload = raw
        else:
            return None

        if not isinstance(payload, dict):
            return None

        try:
            if "addMsgs" in payload or "modContacts" in payload:
                return SyncMessageResponse.model_validate(payload)
            if payload.get("code") == 200 and isinstance(payload.get("data"), dict):
                return SyncMessageResponse.model_validate(payload["data"])
            api_resp = ApiResponse[SyncMessageResponse].model_validate(payload)
            if api_resp.data is not None:
                return api_resp.data
        except Exception as e:
            logger.warning(f"WebSocket 同步消息解析失败: {e}")
        return None

    async def _dispatch_sync(self, resp: SyncMessageResponse) -> None:
        if not resp.addMsgs:
            return
        if self._handler and self.client:
            try:
                await self._handler(self.client, resp)
            except Exception:
                logger.exception("消息处理函数异常")
        elif not self.client:
            logger.error("MsgClient.client 未注入！无法调用消息处理器")

    async def _ws_loop(self, wxid: str) -> None:
        """按 wxid 维持独立 WebSocket 长连接接收同步消息。"""
        base_url = self.t._config.base_url
        ws_url = build_msg_ws_url(base_url, wxid)
        logger.success(f"微信消息 WebSocket 已启动: {ws_url}")

        reconnect_delay = 2.0
        while not self._stop_event.is_set():
            session: Optional[aiohttp.ClientSession] = None
            try:
                session = aiohttp.ClientSession()
                self._ws_session = session
                async with session.ws_connect(
                    ws_url,
                    heartbeat=30,
                    receive_timeout=None,
                ) as ws:
                    reconnect_delay = 2.0
                    async for msg in ws:
                        if self._stop_event.is_set():
                            break
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            resp = self._parse_sync_payload(msg.data)
                            if resp:
                                await self._dispatch_sync(resp)
                        elif msg.type == aiohttp.WSMsgType.BINARY:
                            resp = self._parse_sync_payload(msg.data)
                            if resp:
                                await self._dispatch_sync(resp)
                        elif msg.type in (
                            aiohttp.WSMsgType.CLOSED,
                            aiohttp.WSMsgType.ERROR,
                        ):
                            break
            except asyncio.CancelledError:
                break
            except Exception as e:
                if not self._stop_event.is_set():
                    logger.warning(f"WebSocket 连接异常: {e}")
            finally:
                if session is not None and not session.closed:
                    await session.close()
                if self._ws_session is session:
                    self._ws_session = None

            if self._stop_event.is_set():
                break
            await asyncio.sleep(reconnect_delay)
            reconnect_delay = min(reconnect_delay * 1.5, 30.0)

        logger.info("消息 WebSocket 已停止")

    # ==================== 启动监听 ====================
    def start(
        self,
        handler: MessageHandler,
        *,
        mode: str | SyncMode = "poll",
        wxid: Optional[str] = None,
    ):
        """
        启动消息监听，回调会收到完整的 LwApiClient 实例。

        Args:
            handler: 消息处理回调
            mode: poll（HTTP 长轮询）或 websocket（每 wxid 一条 WS）
            wxid: WebSocket 模式必填；未传时使用 client.wxid
        """
        if self._task and not self._task.done():
            logger.warning("消息监听已启动，请勿重复启动")
            return

        if not self.client:
            logger.error("MsgClient.client 未设置！请确保在 LwApiClient 中注入了 self.msg.client = self")
            return

        try:
            sync_mode = normalize_sync_mode(mode)
        except ValueError as e:
            logger.error(str(e))
            return

        effective_wxid = (wxid or self.client.wxid or "").strip()
        if sync_mode == "websocket" and not effective_wxid:
            logger.error("WebSocket 同步需要 wxid，请先登录或传入 wxid")
            return

        self._handler = handler
        self._sync_mode = sync_mode
        self._stop_event.clear()

        if sync_mode == "websocket":
            self._task = asyncio.create_task(self._ws_loop(effective_wxid))
            logger.success(f"消息 WebSocket 启动成功 (wxid={effective_wxid})")
        else:
            self._task = asyncio.create_task(self._polling_loop())
            logger.success("消息长轮询启动成功")

    @property
    def sync_mode(self) -> SyncMode:
        return self._sync_mode

    # ==================== 停止监听 ====================
    def stop(self):
        """停止消息监听（轮询或 WebSocket）"""
        self._stop_event.set()
        if self._task:
            self._task.cancel()

    async def wait_stop(self):
        """等待监听任务彻底结束（优雅退出时使用）"""
        if self._task:
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        if self._ws_session and not self._ws_session.closed:
            await self._ws_session.close()
            self._ws_session = None
            
            
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

    async def revoke_message(
        self,
        *,
        new_msg_id: Optional[int] = None,
        client_msg_id: Optional[int] = None,
        create_time: Optional[int] = None,
        to_user_name: Optional[str] = None,
        wxid: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> Any:
        """撤回消息（按服务端要求填写标识字段）。"""
        return await self.t.post(
            "/Msg/Revoke",
            json=RevokeMsgParam(
                new_msg_id=new_msg_id,
                client_msg_id=client_msg_id,
                create_time=create_time,
                to_user_name=to_user_name,
                wxid=wxid,
            ).to_api(),
            timeout=timeout,
        )

    async def send_app_message(
        self, to_wxid: str, xml: str, msg_type: int, *, timeout: Optional[float] = None
    ) -> Any:
        """发送小程序消息。"""
        return await self.t.post(
            "/Msg/SendApp",
            json=SendAppMsgParam(to_wxid=to_wxid, xml=xml, msg_type=msg_type).to_api(),
            timeout=timeout,
        )

    async def send_cdn_file(
        self, to_wxid: str, content_xml: str, *, timeout: Optional[float] = None
    ) -> Any:
        """转发 CDN 文件消息（content 为消息 XML）。"""
        return await self.t.post(
            "/Msg/SendCDNFile",
            json=MsgForwardXmlParam(to_wxid=to_wxid, content=content_xml).to_api(),
            timeout=timeout,
        )

    async def send_cdn_image(
        self, to_wxid: str, content_xml: str, *, timeout: Optional[float] = None
    ) -> Any:
        """转发 CDN 图片消息。"""
        return await self.t.post(
            "/Msg/SendCDNImg",
            json=MsgForwardXmlParam(to_wxid=to_wxid, content=content_xml).to_api(),
            timeout=timeout,
        )

    async def send_cdn_video(
        self, to_wxid: str, content_xml: str, *, timeout: Optional[float] = None
    ) -> Any:
        """转发 CDN 视频消息。"""
        return await self.t.post(
            "/Msg/SendCDNVideo",
            json=MsgForwardXmlParam(to_wxid=to_wxid, content=content_xml).to_api(),
            timeout=timeout,
        )

    async def send_emoji(
        self, to_wxid: str, total_len: int, md5: str, *, timeout: Optional[float] = None
    ) -> Any:
        """发送表情消息。"""
        return await self.t.post(
            "/Msg/SendEmoji",
            json=SendEmojiParam(to_wxid=to_wxid, total_len=total_len, md5=md5).to_api(),
            timeout=timeout,
        )

    async def send_quote_message(
        self,
        to_wxid: str,
        fromusr: str,
        displayname: str,
        new_msg_id: str,
        msg_content: str,
        quote_content: str,
        msg_seq: str = "0",
        *,
        timeout: Optional[float] = None,
    ) -> Any:
        """发送引用消息。"""
        return await self.t.post(
            "/Msg/SendQuote",
            json=SendQuoteMsgParam(
                to_wxid=to_wxid,
                fromusr=fromusr,
                displayname=displayname,
                new_msg_id=new_msg_id,
                msg_content=msg_content,
                quote_content=quote_content,
                msg_seq=msg_seq,
            ).to_api(),
            timeout=timeout,
        )

    async def send_video_message(
        self,
        to_wxid: str,
        play_length: int,
        video_b64: str,
        image_base64: str,
        *,
        timeout: Optional[float] = None,
    ) -> Any:
        """发送视频消息（视频与封面均为 Base64）。"""
        return await self.t.post(
            "/Msg/SendVideo",
            json=SendVideoMsgParam(
                to_wxid=to_wxid,
                play_length=play_length,
                video_b64=video_b64,
                image_base64=image_base64,
            ).to_api(),
            timeout=timeout,
        )

    async def send_voice_message(
        self,
        to_wxid: str,
        voice_b64: str,
        voice_type: int,
        voice_time_ms: int,
        wxid: Optional[str] = None,
        *,
        timeout: Optional[float] = None,
    ) -> Any:
        """发送语音消息（voice_type：AMR=0, MP3=2 等；voice_time_ms 为毫秒）。"""
        return await self.t.post(
            "/Msg/SendVoice",
            json=SendVoiceMessageParam(
                to_wxid=to_wxid,
                voice_b64=voice_b64,
                voice_type=voice_type,
                voice_time=voice_time_ms,
                wxid=wxid,
            ).to_api(),
            timeout=timeout,
        )

    async def share_card(
        self,
        to_wxid: str,
        card_wx_id: str,
        card_nick_name: str,
        card_alias: str = "",
        *,
        timeout: Optional[float] = None,
    ) -> Any:
        """分享名片。"""
        return await self.t.post(
            "/Msg/ShareCard",
            json=ShareCardParam(
                to_wxid=to_wxid,
                card_wx_id=card_wx_id,
                card_nick_name=card_nick_name,
                card_alias=card_alias,
            ).to_api(),
            timeout=timeout,
        )

    async def share_link_message(
        self,
        to_wxid: str,
        title: str,
        desc: str,
        url: str,
        thumb_url: str,
        *,
        timeout: Optional[float] = None,
    ) -> Any:
        """发送分享链接消息。"""
        return await self.t.post(
            "/Msg/ShareLink",
            json=SendShareLinkMsgParam(
                to_wxid=to_wxid, title=title, desc=desc, url=url, thumb_url=thumb_url
            ).to_api(),
            timeout=timeout,
        )

    async def share_location(
        self,
        to_wxid: str,
        x: float,
        y: float,
        scale: float = 1.0,
        label: str = "",
        poiname: str = "",
        infourl: str = "",
        *,
        timeout: Optional[float] = None,
    ) -> Any:
        """分享地理位置。"""
        return await self.t.post(
            "/Msg/ShareLocation",
            json=ShareLocationParam(
                to_wxid=to_wxid,
                x=x,
                y=y,
                scale=scale,
                label=label,
                poiname=poiname,
                infourl=infourl,
            ).to_api(),
            timeout=timeout,
        )

    async def share_video_message(
        self, to_wxid: str, xml: str, *, timeout: Optional[float] = None
    ) -> Any:
        """分享视频（XML 消息体）。"""
        return await self.t.post(
            "/Msg/ShareVideo",
            json=ShareVideoXmlParam(to_wxid=to_wxid, xml=xml).to_api(),
            timeout=timeout,
        )

    async def upload_image_base64(
        self, to_wxid: str, image_b64: str, *, timeout: Optional[float] = None
    ) -> Any:
        """发送图片消息（直接传 Base64，不经 URL 下载）。"""
        return await self.t.post(
            "/Msg/UploadImg",
            json=SendImageMsgParam(to_wxid=to_wxid, image_b64=image_b64).to_api(),
            timeout=timeout,
        )
    

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

        return await self.upload_image_base64(to_wxid, base64_str, timeout=float(timeout))