
class Session:
    """SDK 会话对象，动态存储 wxid"""
    def __init__(self):
        self.wxid = None
    def is_logged_in(self):
        return bool(self.wxid)
    def set_wxid(self, wxid: str):
        self.wxid = wxid
