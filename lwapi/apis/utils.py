# lwapi/apis/utils.py
from __future__ import annotations

import asyncio

from functools import wraps
from typing import (
    TypeVar,
    Generic,
    Callable,
    Awaitable,
    Any,
    get_origin,
    get_args,
    Union,
)
from loguru import logger
from ..models.base import ResponseResult

T = TypeVar("T")


class ApiResponse(Generic[T]):
    def __init__(self, raw: ResponseResult, data: Any = None):
        self.raw = raw
        self.data = data
        self.code = raw.code
        self.message = raw.message or ""

    @property
    def ok(self) -> bool:
        return self.code == 200 and self.data is not None

    def __bool__(self) -> bool:
        return self.ok

    def __repr__(self) -> str:
        return f"<ApiResponse code={self.code} ok={self.ok}>"


def api_call(
    success_code: int = 200,
    return_on_fail: Any = None,
    log_error: bool = True,  # 网络异常打印 error
    log_business: bool = False,  # 业务失败是否打印 warning（推荐 False，安静）
):
    """
    最终生产版：
    - 网络异常 → error（必须看到）
    - 业务失败（code!=200）→ debug（不吵）
    - 模型解析失败 → error
    """

    def decorator(
        func: Callable[..., Awaitable[ResponseResult]],
    ) -> Callable[..., Awaitable[ApiResponse]]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> ApiResponse:
            try:
                result: ResponseResult = await func(*args, **kwargs)

                # 业务失败（code != 200）
                if result.code != success_code:
                    if log_business:
                        logger.warning(
                            f"业务失败 ← {func.__name__} code={result.code} msg={result.message}"
                        )
                    else:
                        logger.debug(f"业务失败 ← {func.__name__} code={result.code}")
                    return ApiResponse(result, return_on_fail)

                if result.data is None:
                    logger.debug(f"成功但 data 为空 ← {func.__name__}")
                    return ApiResponse(result, return_on_fail)

                return_type = func.__annotations__.get("return")
                if get_origin(return_type) is Union:
                    args = [a for a in get_args(return_type) if a is not type(None)]
                    return_type = args[0] if args else None

                if return_type and hasattr(return_type, "model_validate"):
                    try:
                        parsed = return_type.model_validate(result.data)
                        return ApiResponse(result, parsed)
                    except Exception as e:
                        logger.error(f"模型解析失败 {return_type.__name__}: {e}")
                        logger.error(f"原始数据: {result.data}")
                        return ApiResponse(result, return_on_fail)
                else:
                    return ApiResponse(result, result.data)

            except asyncio.CancelledError:
                raise  # 让任务正常退出
            except Exception as e:
                logger.debug(f"请求异常 ← {func.__name__}: {type(e).__name__}: {e}")
                return ApiResponse(
                    ResponseResult(code=-1, message=f"{type(e).__name__}: {e}"),
                    return_on_fail,
                )

        return wrapper

    return decorator
