# lwapi/models/relay.py
from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import Field

from ..models import BaseModelWithConfig


class RelayProxyInfo(BaseModelWithConfig):
    """Relay Init 可选代理（仅服务端存会话用，客户端 POST 微信不走代理）。"""

    proxyIp: str = ""
    proxyUser: str = ""
    proxyPassword: str = ""


class HttpSpec(BaseModelWithConfig):
    method: str = "POST"
    url: str = ""
    headers: Dict[str, str] = Field(default_factory=dict)
    body: str = ""


class InitPrepareRequest(BaseModelWithConfig):
    deviceId: Optional[str] = None
    osType: int = 0
    proxy: Optional[RelayProxyInfo] = None
    sessionId: Optional[str] = None


class InitPrepareData(BaseModelWithConfig):
    sessionId: str = ""
    inited: bool = False
    http: Optional[HttpSpec] = None


class InitCompleteRequest(BaseModelWithConfig):
    sessionId: str
    statusCode: int = 200
    body: str = ""


class InitCompleteData(BaseModelWithConfig):
    sessionId: str = ""
    inited: bool = False


class BizPrepareRequest(BaseModelWithConfig):
    sessionId: str
    flow: str
    wxid: Optional[str] = None


class BizPrepareData(BaseModelWithConfig):
    sessionId: str = ""
    flow: str = ""
    http: Optional[HttpSpec] = None
    needInit: bool = False
    needInitReason: Optional[str] = None


class BizCompleteRequest(BaseModelWithConfig):
    sessionId: str
    flow: str
    statusCode: int = 200
    body: str = ""


class BizCompleteData(BaseModelWithConfig):
    sessionId: str = ""
    flow: str = ""
    result: Dict[str, Any] = Field(default_factory=dict)
