# lwapi/apis/label.py
"""微信标签。"""

from __future__ import annotations

from typing import Any, Optional

from ..models.label_requests import (
    LabelAddParam,
    LabelDeleteParam,
    LabelUpdateListParam,
    LabelUpdateNameParam,
)
from ..transport import AsyncHTTPTransport


class LabelClient:
    def __init__(self, transport: AsyncHTTPTransport) -> None:
        self._t = transport

    async def add(self, label_name: str, *, timeout: Optional[float] = None) -> Any:
        """新建标签。"""
        return await self._t.post(
            "/Label/Add", json=LabelAddParam(label_name=label_name).to_api(), timeout=timeout
        )

    async def delete(self, label_id: str, *, timeout: Optional[float] = None) -> Any:
        """删除标签。"""
        return await self._t.post(
            "/Label/Delete", json=LabelDeleteParam(label_id=label_id).to_api(), timeout=timeout
        )

    async def get_list(self, *, timeout: Optional[float] = None) -> Any:
        """获取标签列表。"""
        return await self._t.post("/Label/GetList", json=None, timeout=timeout)

    async def update_list(
        self, label_id: str, to_wxids: str, *, timeout: Optional[float] = None
    ) -> Any:
        """更新标签成员（to_wxids 逗号分隔）。"""
        return await self._t.post(
            "/Label/UpdateList",
            json=LabelUpdateListParam(label_id=label_id, to_wxids=to_wxids).to_api(),
            timeout=timeout,
        )

    async def update_name(
        self, label_id: int, new_name: str, *, timeout: Optional[float] = None
    ) -> Any:
        """修改标签名称。"""
        return await self._t.post(
            "/Label/UpdateName",
            json=LabelUpdateNameParam(label_id=label_id, new_name=new_name).to_api(),
            timeout=timeout,
        )
