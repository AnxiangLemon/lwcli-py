
class LoginApi:
    """登录相关 API"""
    def __init__(self, http, session):
        self.http = http
        self.session = session

    def login(self, username: str, password: str):
        body = {"UserName": username, "Password": password}
        result = self.http.post("/Login/Login", body=body, require_login=False)
        wxid = result.get("Data", {}).get("Wxid")
        if wxid:
            self.session.set_wxid(wxid)
        return result
