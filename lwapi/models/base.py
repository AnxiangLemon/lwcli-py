from pydantic import BaseModel
from typing import Any, Optional

class ResponseResult(BaseModel):
    RetCode: int
    RetMsg: str = ""
    Data: Optional[Any] = None
