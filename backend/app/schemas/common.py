"""通用 API 响应模型与辅助函数。"""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """统一响应包装：{code, message, data, request_id}。"""

    code: str = "OK"
    message: str = "success"
    data: T = None  # type: ignore[assignment]
    request_id: str = ""


class Page(BaseModel, Generic[T]):
    """分页模型，泛型支持任意 item 类型。"""

    items: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int

    @classmethod
    def create(cls, items: list[T], total: int, page: int, page_size: int) -> Page[T]:
        """根据总数和分页参数构造 Page 对象，自动计算 total_pages。"""
        total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0
        return cls(items=items, total=total, page=page, page_size=page_size, total_pages=total_pages)


def ok(data: Any = None, request: Request | None = None) -> dict:
    """返回标准成功响应体。"""
    return {
        "code": "OK",
        "message": "success",
        "data": data,
        "request_id": (request.headers.get("X-Request-ID", "") if request else ""),
    }


def error(
    code: str, message: str, data: Any = None, status_code: int = 400, request: Request | None = None
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "code": code,
            "message": message,
            "data": data or {},
            "request_id": (request.headers.get("X-Request-ID", "") if request else ""),
        },
    )
