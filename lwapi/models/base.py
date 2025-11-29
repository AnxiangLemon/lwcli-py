# models/base.py
from pydantic import BaseModel, Field
from typing import Any

def alias_generator(s: str) -> str:
    """将字段名转换为响应数据中的字段名"""
    return s  # 如果你希望字段名不改变，可以直接返回原字段名

class ResponseResult(BaseModel):
    """API响应的基础结构"""
    RetCode: int = Field(..., alias="code", description="返回码")
    message: str = Field(..., description="错误信息或成功信息")
    data: Any = Field(None, description="响应数据")
    
    class Config:
        # 使用定义好的 alias_generator 函数来转换字段名
        alias_generator = alias_generator
        # 忽略不存在的字段
        extra = "ignore"
