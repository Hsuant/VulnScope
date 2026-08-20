"""request_id 贯穿：生成、上下文注入、HTTP 中间件。

- 优先透传客户端 ``X-Request-ID``（外部链路沿用同一 ID），否则生成 ``vsh-`` 前缀 ID。
- 生成的 ID 直接注入 ASGI scope 的 ``x-request-id`` 请求头 —— 下游
  ``request.headers.get("X-Request-ID")``（响应体 ``ok()``/``error()`` 与异常
  处理器）无需改动即可读到完整链路 ID，且外部链路 ID 恒优先。
- contextvars 同一来源，供日志 Filter 贯穿结构化日志。
- 中间件始终回写 ``X-Request-ID`` 响应头。
"""

from __future__ import annotations

import contextvars
import uuid
from collections.abc import Awaitable, Callable, MutableMapping

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="")


def generate_request_id() -> str:
    """生成请求 ID：vsh- + uuid4 hex 前 16 位（紧凑、可辨识）。"""
    return "vsh-" + uuid.uuid4().hex[:16]


def get_request_id() -> str:
    """当前请求的 request_id（中间件之外为空串）。"""
    return request_id_var.get()


_HEADER_NAME = b"x-request-id"


def _raw_header(headers: list[tuple[bytes, bytes]], name: bytes) -> str:
    """从 ASGI scope 原始 headers 取首个匹配值（避免触发 Request.headers 缓存）。"""
    for key, value in headers:
        if key.lower() == name:
            return value.decode("utf-8")
    return ""


def _inject_request_header(scope: MutableMapping, value: str) -> None:
    """向 ASGI scope 的 headers 覆盖写入 x-request-id（下游 headers 不可变）。

    必须在本中间件 dispatch 且下游尚未读取 headers 前完成——本模块全程用
    ``_raw_header`` 读取原始字节，绝不触碰 ``request.headers`` 属性缓存。
    """
    headers = [(k, v) for k, v in scope.get("headers", []) if k.lower() != _HEADER_NAME]
    headers.append((_HEADER_NAME, value.encode("utf-8")))
    scope["headers"] = headers


class RequestIdContextMiddleware(BaseHTTPMiddleware):
    """请求级 request_id 生命周期管理。

    放行前写入 contextvar 并注入请求头；响应统一写 ``X-Request-ID`` 头。
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        incoming = _raw_header(request.scope.get("headers", []), _HEADER_NAME).strip()
        request_id = incoming if incoming else generate_request_id()
        # 注入下游可见的请求头（客户端未带时补全），保持 ok()/error() 的头读取兼容。
        _inject_request_header(request.scope, request_id)
        token = request_id_var.set(request_id)
        try:
            response = await call_next(request)
        finally:
            request_id_var.reset(token)
        response.headers.setdefault("X-Request-ID", request_id)
        return response
