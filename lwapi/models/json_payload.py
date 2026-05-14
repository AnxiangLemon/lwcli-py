# lwapi/models/json_payload.py
"""LwApi 请求体 JSON 序列化基类（与各业务 models 共用）。"""

from __future__ import annotations

from typing import Any

from . import BaseModelWithConfig


class ApiJsonBody(BaseModelWithConfig):
    """输出与 swagger 一致的 camelCase JSON，供 ``AsyncHTTPTransport.post`` 使用。"""

    def to_api(self) -> dict[str, Any]:
        return self.model_dump(mode="json", by_alias=True, exclude_none=True)
