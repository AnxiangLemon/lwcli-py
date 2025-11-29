# lwapi/exceptions.py

class LwApiError(Exception):
    """基类异常，用于所有 lwapi 相关错误"""

class HttpError(LwApiError):
    """HTTP 错误异常"""
    def __init__(self, status_code: int, message: str):
        super().__init__(f"HTTP 错误 {status_code}: {message}")
        self.status_code = status_code
        self.message = message

class ApiError(LwApiError):
    """API 业务错误异常"""
    def __init__(self, code: int, message: str):
        super().__init__(f"API 错误 {code}: {message}")
        self.code = code
        self.message = message
