# lwapi/models/base.py
from __future__ import annotations

from typing import Generic, TypeVar
from pydantic import  Field
from ..models import BaseModelWithConfig

# 泛型变量，用于让 transport.post 返回具体类型
T = TypeVar("T")


class ApiResponse(BaseModelWithConfig, Generic[T]):
    """
    所有 LwApi 接口返回的最外层结构
    注意：这个类永远不会暴露给业务代码！
    """
    code: int = Field(..., description="返回码，200 表示成功")
    message: str = Field("", description="错误信息")
    data: T = Field(None, description="真实业务数据")

