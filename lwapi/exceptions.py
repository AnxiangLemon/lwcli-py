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


class ApiError(Exception):
    """API 业务层错误（code != 200）"""
    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message
        super().__init__(f"API [{code}]: {message}")

# 可以扩展其他异常，如 LoginError(ApiError): ...
class LoginError(ApiError):
    """登录专用异常"""
    pass