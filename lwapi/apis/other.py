# lwapi/apis/other.py
"""下载、CDN、杂项：参数由 SDK 组装。"""

from __future__ import annotations

from typing import Any, Optional

from ..models.other_requests import (
    MiscCdnDownloadImageParam,
    MiscDownloadAppAttachParam,
    MiscDownloadParam,
    MiscDownloadVoiceParam,
    MiscGetA8KeyParam,
    MiscSection,
    MiscThirdAppGrantParam,
)
from ..transport import AsyncHTTPTransport


class OtherClient:
    def __init__(self, transport: AsyncHTTPTransport) -> None:
        self._t = transport

    async def cdn_download_image(
        self, file_no: str, file_aes_key: str, *, timeout: Optional[float] = None
    ) -> Any:
        """CDN 下载高清图。"""
        return await self._t.post(
            "/Other/CdnDownloadImage",
            json=MiscCdnDownloadImageParam(file_no=file_no, file_aes_key=file_aes_key).to_api(),
            timeout=timeout,
        )

    async def download_file(
        self,
        app_id: str,
        attach_id: str,
        user_name: str,
        data_len: int,
        section_start: int,
        section_len: int,
        *,
        timeout: Optional[float] = None,
    ) -> Any:
        """下载消息文件附件。"""
        sec = MiscSection(start_pos=section_start, data_len=section_len)
        return await self._t.post(
            "/Other/DownloadFile",
            json=MiscDownloadAppAttachParam(
                app_id=app_id,
                attach_id=attach_id,
                user_name=user_name,
                data_len=data_len,
                section=sec,
            ).to_api(),
            timeout=timeout,
        )

    async def download_img(
        self,
        to_wxid: str,
        msg_id: int,
        data_len: int,
        section_start: int,
        section_len: int,
        compress_type: int = 0,
        *,
        timeout: Optional[float] = None,
    ) -> Any:
        """下载消息内高清图片。"""
        sec = MiscSection(start_pos=section_start, data_len=section_len)
        return await self._t.post(
            "/Other/DownloadImg",
            json=MiscDownloadParam(
                to_wxid=to_wxid,
                msg_id=msg_id,
                data_len=data_len,
                section=sec,
                compress_type=compress_type,
            ).to_api(),
            timeout=timeout,
        )

    async def download_video(
        self,
        to_wxid: str,
        msg_id: int,
        data_len: int,
        section_start: int,
        section_len: int,
        compress_type: int = 0,
        *,
        timeout: Optional[float] = None,
    ) -> Any:
        """下载消息内视频。"""
        sec = MiscSection(start_pos=section_start, data_len=section_len)
        return await self._t.post(
            "/Other/DownloadVideo",
            json=MiscDownloadParam(
                to_wxid=to_wxid,
                msg_id=msg_id,
                data_len=data_len,
                section=sec,
                compress_type=compress_type,
            ).to_api(),
            timeout=timeout,
        )

    async def download_voice(
        self,
        bufid: str,
        from_user_name: str,
        length: int,
        msg_id: int,
        *,
        timeout: Optional[float] = None,
    ) -> Any:
        """下载语音。"""
        return await self._t.post(
            "/Other/DownloadVoice",
            json=MiscDownloadVoiceParam(
                bufid=bufid,
                from_user_name=from_user_name,
                length=length,
                msg_id=msg_id,
            ).to_api(),
            timeout=timeout,
        )

    async def get_a8key(
        self,
        req_url: str,
        scene: int = 4,
        op_code: int = 2,
        *,
        timeout: Optional[float] = None,
    ) -> Any:
        """获取 A8Key（常用字段已给默认值，可按需扩展模型）。"""
        return await self._t.post(
            "/Other/GetA8Key",
            json=MiscGetA8KeyParam(req_url=req_url, scene=scene, op_code=op_code).to_api(),
            timeout=timeout,
        )

    async def get_bound_hard_devices(self, *, timeout: Optional[float] = None) -> Any:
        """获取已绑定硬件列表。"""
        return await self._t.post("/Other/GetBoundHardDevices", json=None, timeout=timeout)

    async def get_cdn_dns(self, *, timeout: Optional[float] = None) -> Any:
        """获取 CDN DNS。"""
        return await self._t.post("/Other/GetCdnDns", json=None, timeout=timeout)

    async def third_app_grant(self, appid: str, *, timeout: Optional[float] = None) -> Any:
        """第三方应用授权。"""
        return await self._t.post(
            "/Other/ThirdAppGrant",
            json=MiscThirdAppGrantParam(appid=appid).to_api(),
            timeout=timeout,
        )
