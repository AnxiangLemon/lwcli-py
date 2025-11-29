
import requests
from .exceptions import LwApiError
from .session import Session

class HttpClient:
    def __init__(self, base_url: str, session: Session):
        self.base_url = base_url.rstrip("/")
        self.session = session
        self.s = requests.Session()

    def post(self, path, body=None, headers=None, params=None, require_login=True):
        url = f"{self.base_url}{path}"
        headers = headers or {}
        if require_login:
            if not self.session.is_logged_in():
                raise LwApiError("请先登录")
            headers["X-Wxid"] = self.session.wxid
        r = self.s.post(url, json=body, headers=headers, params=params)
        return r.json()

class LwApiClient:
    def __init__(self, base_url: str):
        self.session = Session()
        self.http = HttpClient(base_url, self.session)

        from .apis.login import LoginApi
        self.login = LoginApi(self.http, self.session)
