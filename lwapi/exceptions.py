# lwapi/exceptions.py

class LwApiError(Exception):
    """基类异常，用于所有 lwapi 相关错误"""

class HttpError(LwApiError):
    """HTTP 错误异常"""
    def __init__(self, status_code: int, message: str):
        super().__init__(f"HTTP 错误 {status_code}: {message}")
        self.status_code = status_code
        self.message = message


