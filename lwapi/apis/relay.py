# lwapi/apis/relay.py
from __future__ import annotations

import asyncio
from typing import Any, Dict, Optional

import httpx
from loguru import logger

from ..exceptions import ApiError, HttpError, LoginError
from ..models.relay import (
    BizCompleteData,
    BizCompleteRequest,
    BizPrepareData,
    BizPrepareRequest,
    HttpSpec,
    InitCompleteData,
    InitCompleteRequest,
    InitPrepareData,
    InitPrepareRequest,
    RelayProxyInfo,
)
from ..transport import AsyncHTTPTransport

_HEX_PREVIEW = 96


def _preview_hex(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    text = value.strip()
    if not text:
        return value
    if len(text) <= _HEX_PREVIEW:
        return text
    return f"{text[:_HEX_PREVIEW]}...({len(text)} hex)"


def _summarize_relay_value(key: str, value: Any) -> Any:
    if value is None:
        return None
    if key in ("body", "Body"):
        return _preview_hex(value)
    if key in ("qrImage", "QrImage", "qr_image"):
        if not isinstance(value, str):
            return value
        text = value.strip()
        if not text:
            return value
        return f"<base64 len={len(text)}>"
    if key == "http" and isinstance(value, dict):
        return _summarize_relay_payload(value)
    if key == "result" and isinstance(value, dict):
        return _summarize_relay_payload(value)
    if isinstance(value, dict):
        return _summarize_relay_payload(value)
    if isinstance(value, list):
        return [_summarize_relay_value("", item) for item in value]
    return value


def _summarize_relay_payload(payload: Optional[dict]) -> Optional[dict]:
    if not payload:
        return payload
    out: Dict[str, Any] = {}
    for key, value in payload.items():
        out[key] = _summarize_relay_value(key, value)
    return out


def _to_hex(data: bytes) -> str:
    return data.hex()


class RelayClient:
    """Relay 登录：lwapi 组包，客户端用本机 IP POST 微信 MMTLS。"""

    def __init__(self, transport: AsyncHTTPTransport):
        self.t = transport
        self._session_id = ""
        self._wechat = httpx.AsyncClient(trust_env=False, timeout=30.0)

    @property
    def session_id(self) -> str:
        return self._session_id

    async def aclose(self) -> None:
        await self._wechat.aclose()

    async def _relay_post(
        self,
        path: str,
        json: Optional[dict] = None,
    ) -> tuple[int, str, Optional[dict]]:
        logger.debug(
            "Relay → {} request: {}",
            path,
            _summarize_relay_payload(json),
        )
        code, message, data = await self.t.post_envelope(path, json=json)
        logger.debug(
            "Relay ← {} response: code={}, message={!r}, data={}",
            path,
            code,
            message,
            _summarize_relay_payload(data),
        )
        return code, message, data

    async def post_wechat(self, spec: HttpSpec) -> tuple[int, bytes]:
        """按 HttpSpec 向微信 POST，禁用系统代理以保证本地出口 IP。"""
        body_hex = (spec.body or "").strip()
        try:
            body = bytes.fromhex(body_hex)
        except ValueError as e:
            raise LoginError(f"http.body hex 解码失败: {e}") from e

        headers = dict(spec.headers or {})
        logger.debug(
            "Relay → WeChat POST {} headers={} body={}",
            spec.url,
            headers,
            _preview_hex(body_hex),
        )
        try:
            resp = await self._wechat.post(
                spec.url,
                content=body,
                headers=headers,
            )
        except httpx.TimeoutException as e:
            raise HttpError(0, f"post wechat timeout: {e}") from e
        except httpx.NetworkError as e:
            raise HttpError(0, f"post wechat network error: {e}") from e

        raw = resp.content
        logger.debug(
            "Relay ← WeChat response: status={} body={}",
            resp.status_code,
            _preview_hex(_to_hex(raw)),
        )
        return resp.status_code, raw

    async def _init_prepare(
        self,
        *,
        device_id: str = "",
        os_type: int = 0,
        proxy: Optional[RelayProxyInfo] = None,
    ) -> InitPrepareData:
        if self._session_id:
            req = InitPrepareRequest(sessionId=self._session_id)
        else:
            req = InitPrepareRequest(
                deviceId=device_id,
                osType=os_type,
                proxy=proxy or RelayProxyInfo(),
            )
        code, message, data = await self._relay_post(
            "/Login/Relay/Init/Prepare",
            json=req.model_dump(exclude_none=True),
        )
        if code == -1019:
            self._session_id = ""
            raise LoginError(message or "Relay 会话已过期", reason="expired")
        if code != 200 or not data:
            raise ApiError(code, message or "Init/Prepare 失败")

        prep = InitPrepareData.model_validate(data)
        if prep.sessionId:
            self._session_id = prep.sessionId
        return prep

    async def _init_complete(self, status_code: int, body_hex: str) -> InitCompleteData:
        if not self._session_id:
            raise LoginError("缺少 Relay sessionId")
        req = InitCompleteRequest(
            sessionId=self._session_id,
            statusCode=status_code,
            body=body_hex,
        )
        code, message, data = await self._relay_post(
            "/Login/Relay/Init/Complete",
            json=req.model_dump(),
        )
        if code != 200 or not data:
            raise ApiError(code, message or "Init/Complete 失败")
        done = InitCompleteData.model_validate(data)
        if done.sessionId:
            self._session_id = done.sessionId
        return done

    async def ensure_init(
        self,
        device_id: str,
        *,
        os_type: int = 0,
        proxy: Optional[RelayProxyInfo] = None,
    ) -> None:
        """Init/Prepare → [POST 微信] → Init/Complete，直至 inited=true。"""
        prep = await self._init_prepare(
            device_id=device_id,
            os_type=os_type,
            proxy=proxy,
        )
        if prep.inited:
            return
        if not prep.http:
            raise LoginError("Init/Prepare 未返回 http 规格")

        status, raw = await self.post_wechat(prep.http)
        await self._init_complete(status, _to_hex(raw))

    async def _biz_prepare(
        self,
        flow: str,
        *,
        wxid: Optional[str] = None,
    ) -> tuple[int, str, BizPrepareData]:
        if not self._session_id:
            raise LoginError("缺少 Relay sessionId，请先 Init")
        req = BizPrepareRequest(sessionId=self._session_id, flow=flow, wxid=wxid)
        code, message, data = await self._relay_post(
            "/Login/Relay/Biz/Prepare",
            json=req.model_dump(exclude_none=True),
        )
        if not data:
            return code, message, BizPrepareData()
        prep = BizPrepareData.model_validate(data)
        if prep.sessionId:
            self._session_id = prep.sessionId
        return code, message, prep

    async def _biz_complete(
        self,
        flow: str,
        status_code: int,
        body_hex: str,
    ) -> tuple[int, str, BizCompleteData]:
        """返回 (code, message, data)；-2020/needInit 不在此抛错，由 biz_round 重试 Init。"""
        if not self._session_id:
            raise LoginError("缺少 Relay sessionId")
        req = BizCompleteRequest(
            sessionId=self._session_id,
            flow=flow,
            statusCode=status_code,
            body=body_hex,
        )
        code, message, data = await self._relay_post(
            "/Login/Relay/Biz/Complete",
            json=req.model_dump(),
        )
        if code == -1019:
            self._session_id = ""
            raise LoginError(message or "Relay 会话已过期", reason="expired")
        if not data:
            raise ApiError(code, message or "Biz/Complete 失败")
        done = BizCompleteData.model_validate(data)
        if done.sessionId:
            self._session_id = done.sessionId
        return code, message, done

    async def biz_round(
        self,
        flow: str,
        *,
        device_id: str = "",
        os_type: int = 0,
        proxy: Optional[RelayProxyInfo] = None,
        wxid: Optional[str] = None,
        max_init_retry: int = 2,
    ) -> Dict[str, Any]:
        """
        Biz/Prepare → [POST 微信] → Biz/Complete，返回 result 字典。
        Prepare 或 Complete 遇 -2020 / needInit 时自动 ensure_init 后重试整条 flow。
        Complete result 遇 ret=-301（host_redirect 换机房）时同样 Init 后重试。
        """
        for attempt in range(max_init_retry + 1):
            code, message, prep = await self._biz_prepare(flow, wxid=wxid)
            if code == -2020 or prep.needInit:
                if attempt >= max_init_retry:
                    raise LoginError(message or "需要先完成 MMTLS 握手")
                logger.info(
                    "Relay Biz/Prepare needInit flow={} attempt={}/{}",
                    flow,
                    attempt + 1,
                    max_init_retry + 1,
                )
                await self.ensure_init(
                    device_id,
                    os_type=os_type,
                    proxy=proxy,
                )
                continue
            if code == -1019:
                self._session_id = ""
                if attempt >= max_init_retry:
                    raise LoginError(message or "Relay 会话已过期", reason="expired")
                await self.ensure_init(
                    device_id,
                    os_type=os_type,
                    proxy=proxy,
                )
                continue
            if code != 200:
                raise ApiError(code, message or f"Biz/Prepare({flow}) 失败")
            if not prep.http:
                raise LoginError(f"Biz/Prepare({flow}) 未返回 http 规格")

            status, raw = await self.post_wechat(prep.http)
            c_code, c_msg, done = await self._biz_complete(flow, status, _to_hex(raw))
            if c_code == -2020 or done.needInit:
                reason = done.needInitReason or "unknown"
                host = done.mmtlsHost or ""
                if attempt >= max_init_retry:
                    raise LoginError(
                        c_msg or f"需要先完成 MMTLS 握手 ({reason})"
                    )
                logger.info(
                    "Relay Biz/Complete needInit flow={} reason={} mmtlsHost={} attempt={}/{}",
                    flow,
                    reason,
                    host,
                    attempt + 1,
                    max_init_retry + 1,
                )
                await self.ensure_init(
                    device_id,
                    os_type=os_type,
                    proxy=proxy,
                )
                continue
            if c_code != 200:
                raise ApiError(c_code, c_msg or "Biz/Complete 失败")
            result = dict(done.result or {})
            if result.get("type") == "error" and int(result.get("ret", 0) or 0) == -301:
                if attempt >= max_init_retry:
                    raise LoginError(
                        c_msg or result.get("msg") or "host_redirect 重试次数已用尽"
                    )
                logger.info(
                    "Relay Biz/Complete host_redirect flow={} ret=-301 attempt={}/{}",
                    flow,
                    attempt + 1,
                    max_init_retry + 1,
                )
                await self.ensure_init(
                    device_id,
                    os_type=os_type,
                    proxy=proxy,
                )
                continue
            return result

        raise LoginError(f"Biz({flow}) 重试次数已用尽")

    async def sec_auto_auth(
        self,
        device_id: str,
        wxid: str,
        *,
        os_type: int = 0,
        proxy: Optional[RelayProxyInfo] = None,
    ) -> Optional[Dict[str, Any]]:
        """Relay 二次免扫码登录，成功返回 login_ok result。"""
        try:
            await self.ensure_init(device_id, os_type=os_type, proxy=proxy)
            result = await self.biz_round(
                "sec_auto_auth",
                device_id=device_id,
                os_type=os_type,
                proxy=proxy,
                wxid=wxid,
            )
        except ApiError as e:
            if e.code == -1019:
                logger.debug(f"Relay 二次登录缓存不可用: {e.message}")
            else:
                logger.warning(f"Relay 二次登录失败: {e}")
            return None
        except LoginError as e:
            logger.debug(f"Relay 二次登录不可用: {e.message}")
            return None
        except HttpError as e:
            logger.warning(f"Relay 二次登录网络异常: {e}")
            return None

        if result.get("type") == "login_ok":
            logger.success("Relay 二次免扫码登录成功")
            return result
        if result.get("type") == "error":
            logger.debug(
                f"Relay 二次登录未成功: ret={result.get('ret')}, msg={result.get('msg')}"
            )
        return None

    async def qr_login_poll(
        self,
        device_id: str,
        *,
        os_type: int = 0,
        proxy: Optional[RelayProxyInfo] = None,
        poll_interval: float = 1.5,
        poll_timeout: float = 300.0,
    ):
        """
        异步迭代 Relay 扫码登录事件，供 WebSocket 推送。
        事件：qr_ready | status | success | error
        """
        await self.ensure_init(device_id, os_type=os_type, proxy=proxy)

        qr_result = await self.biz_round(
            "qr_get",
            device_id=device_id,
            os_type=os_type,
            proxy=proxy,
        )
        if qr_result.get("type") != "qr":
            msg = qr_result.get("msg") or qr_result.get("type") or "获取二维码失败"
            yield {"event": "error", "code": "api", "message": str(msg)}
            return

        qr_image = qr_result.get("qrImage") or ""
        device_out = qr_result.get("deviceId") or device_id
        yield {
            "event": "qr_ready",
            "qr_image": qr_image,
            "device_id": device_out,
        }

        last_scan_state: Optional[int] = None
        last_nick = ""
        last_avatar = ""
        deadline = asyncio.get_running_loop().time() + poll_timeout
        while asyncio.get_running_loop().time() < deadline:
            check = await self.biz_round(
                "qr_check",
                device_id=device_id,
                os_type=os_type,
                proxy=proxy,
            )
            rtype = check.get("type")
            nick_name = str(
                check.get("nickname") or check.get("nickName") or ""
            ).strip()
            head_img_url = str(
                check.get("avatar") or check.get("headImgUrl") or ""
            ).strip()

            if rtype == "qr_status":
                scan_state = int(check.get("scanState", 0) or 0)
                phase_map = {0: "waiting", 1: "scanned", 2: "confirming", 4: "canceled"}
                phase = phase_map.get(scan_state, "unknown")

                if scan_state == 4:
                    if last_scan_state != scan_state:
                        yield {
                            "event": "status",
                            "phase": "canceled",
                            "raw_status": scan_state,
                            "nick_name": nick_name or None,
                            "head_img_url": head_img_url or None,
                        }
                    yield {
                        "event": "error",
                        "code": "canceled",
                        "message": "二维码已被取消",
                    }
                    return

                if (
                    scan_state != last_scan_state
                    or nick_name != last_nick
                    or head_img_url != last_avatar
                ):
                    yield {
                        "event": "status",
                        "phase": phase,
                        "raw_status": scan_state,
                        "nick_name": nick_name or None,
                        "head_img_url": head_img_url or None,
                    }
                    last_scan_state = scan_state
                    last_nick = nick_name
                    last_avatar = head_img_url

                if scan_state in (0, 1):
                    await asyncio.sleep(poll_interval)
                    continue

                yield {
                    "event": "error",
                    "code": "api",
                    "message": f"未知扫码状态: scanState={scan_state}",
                }
                return
            elif rtype == "confirmed":
                yield {
                    "event": "status",
                    "phase": "confirming",
                    "raw_status": check.get("scanState", 2),
                    "nick_name": nick_name or last_nick or None,
                    "head_img_url": head_img_url or last_avatar or None,
                }
                break
            elif rtype == "error":
                yield {
                    "event": "error",
                    "code": "api",
                    "message": check.get("msg") or f"ret={check.get('ret')}",
                    "ret": check.get("ret"),
                }
                return
            else:
                yield {
                    "event": "error",
                    "code": "api",
                    "message": f"未知 qr_check 结果: {rtype}",
                }
                return

        else:
            yield {"event": "error", "code": "timeout", "message": "二维码登录超时"}
            return

        auth = await self.biz_round(
            "sec_manual_auth",
            device_id=device_id,
            os_type=os_type,
            proxy=proxy,
            max_init_retry=3,
        )
        if auth.get("type") == "login_ok":
            yield {
                "event": "success",
                "wxid": auth.get("wxid") or "",
                "nickname": auth.get("nickname") or "",
                "avatar": auth.get("avatar") or "",
                "head_img_url": auth.get("avatar") or "",
            }
            return

        if auth.get("type") == "error":
            yield {
                "event": "error",
                "code": "api",
                "message": auth.get("msg") or f"ret={auth.get('ret')}",
                "ret": auth.get("ret"),
            }
            return

        yield {
            "event": "error",
            "code": "login",
            "message": f"登录未完成: {auth.get('type')}",
        }
