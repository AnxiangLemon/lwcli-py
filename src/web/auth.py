"""
运维台 Token 鉴权：环境变量 LWAPI_WEB_TOKEN（默认 123123），留空则关闭鉴权。
"""

from __future__ import annotations

import hashlib
import hmac
import os
import time
from aiohttp import web
from dotenv import load_dotenv

from src.app_paths import env_file

load_dotenv(env_file())

COOKIE_NAME = "lwapi_session"
ENV_TOKEN = "LWAPI_WEB_TOKEN"
DEFAULT_TOKEN = "123123"

# ip -> (fail_count, window_start)
_login_failures: dict[str, tuple[int, float]] = {}
_MAX_FAILURES = 8
_FAILURE_WINDOW_SEC = 300.0


def get_web_token() -> str:
    return os.getenv(ENV_TOKEN, DEFAULT_TOKEN).strip()


def is_auth_enabled() -> bool:
    return bool(get_web_token())


def _session_cookie_value() -> str:
    secret = get_web_token().encode("utf-8")
    return hmac.new(secret, b"lwapi-web-session-v1", hashlib.sha256).hexdigest()


def verify_token(provided: str) -> bool:
    expected = get_web_token()
    if not expected:
        return True
    return hmac.compare_digest((provided or "").strip(), expected)


def is_authenticated(request: web.Request) -> bool:
    if not is_auth_enabled():
        return True
    cookie = request.cookies.get(COOKIE_NAME, "")
    if cookie and hmac.compare_digest(cookie, _session_cookie_value()):
        return True
    auth = request.headers.get("Authorization", "")
    if auth.lower().startswith("bearer "):
        return verify_token(auth[7:].strip())
    return False


def _client_ip(request: web.Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.remote or "unknown"


def _is_rate_limited(ip: str) -> bool:
    now = time.monotonic()
    count, start = _login_failures.get(ip, (0, now))
    if now - start > _FAILURE_WINDOW_SEC:
        _login_failures[ip] = (0, now)
        return False
    return count >= _MAX_FAILURES


def _record_failure(ip: str) -> None:
    now = time.monotonic()
    count, start = _login_failures.get(ip, (0, now))
    if now - start > _FAILURE_WINDOW_SEC:
        count, start = 0, now
    _login_failures[ip] = (count + 1, start)


def _clear_failures(ip: str) -> None:
    _login_failures.pop(ip, None)


def is_public_path(path: str, method: str) -> bool:
    if path == "/login.html" or path.startswith("/static/"):
        return True
    if path == "/api/auth/login" and method == "POST":
        return True
    if path == "/api/auth/status" and method == "GET":
        return True
    return False


@web.middleware
async def auth_middleware(request: web.Request, handler):
    if not is_auth_enabled() or is_public_path(request.path, request.method):
        return await handler(request)

    if is_authenticated(request):
        return await handler(request)

    if request.path.startswith("/api/") or request.path.startswith("/ws/"):
        return web.json_response({"error": "未登录或 Token 无效"}, status=401)

    raise web.HTTPFound("/login.html")


def set_session_cookie(response: web.Response) -> None:
    response.set_cookie(
        COOKIE_NAME,
        _session_cookie_value(),
        httponly=True,
        samesite="Lax",
        max_age=7 * 24 * 3600,
        path="/",
    )


async def api_auth_login(request: web.Request) -> web.Response:
    ip = _client_ip(request)
    if _is_rate_limited(ip):
        return web.json_response(
            {"error": "登录尝试过多，请稍后再试"},
            status=429,
        )
    try:
        body = await request.json()
    except Exception:
        body = {}
    token = str(body.get("token") or "").strip()
    if not verify_token(token):
        _record_failure(ip)
        return web.json_response({"error": "Token 错误"}, status=401)
    _clear_failures(ip)
    resp = web.json_response({"ok": True})
    set_session_cookie(resp)
    return resp


async def api_auth_logout(request: web.Request) -> web.Response:
    resp = web.json_response({"ok": True})
    resp.del_cookie(COOKIE_NAME, path="/")
    return resp


async def api_auth_status(request: web.Request) -> web.Response:
    return web.json_response(
        {
            "auth_enabled": is_auth_enabled(),
            "authenticated": is_authenticated(request),
        }
    )
