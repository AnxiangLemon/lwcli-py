# lwapi/exceptions.py

class LwApiError(Exception):
    """基类异常，用于所有 lwapi 相关错误"""

# lwapi/exceptions.py
class HttpError(Exception):
    """HTTP 网络层错误（超时、404、500 等）"""
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"HTTP {status_code}: {message}")


def is_wrapped_request_timeout(exc: BaseException) -> bool:
    """transport 将 httpx 超时转为 HttpError(0, 'request timeout') 时的判断。"""
    return isinstance(exc, HttpError) and exc.status_code == 0 and "timeout" in (
        exc.message or ""
    ).lower()


class ApiError(Exception):
    """API 业务层错误（code != 200）"""
    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message
        super().__init__(f"API [{code}]: {message}")

class LoginError(LwApiError):
    """登录流程异常（扫码、二次登录、运维台 emit 等）。"""

    # 用户主动取消、过期、超时等：Bot 可自动重新拉码，不必打 ERROR 堆栈
    RECOVERABLE_REASONS = frozenset(
        {"canceled", "expired", "timeout", "stopped", "login"}
    )

    def __init__(self, message: str, *, reason: str = "") -> None:
        self.message = message
        self.reason = (reason or "").strip()
        super().__init__(message)

    @property
    def recoverable(self) -> bool:
        return self.reason in self.RECOVERABLE_REASONS