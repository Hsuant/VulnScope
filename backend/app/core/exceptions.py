"""统一异常体系：错误码 + HTTP 状态映射 + 全局渲染。"""

from __future__ import annotations

from enum import Enum

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse


class ErrorCode(str, Enum):
    """业务错误码。命名规则：模块_场景。"""

    INTERNAL_ERROR = "INTERNAL_ERROR"
    REQUEST_INVALID = "REQUEST_INVALID"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"

    # auth
    AUTH_INVALID_CREDENTIALS = "AUTH_INVALID_CREDENTIALS"
    AUTH_TOKEN_EXPIRED = "AUTH_TOKEN_EXPIRED"
    AUTH_TOKEN_INVALID = "AUTH_TOKEN_INVALID"
    AUTH_PASSWORD_FORMAT = "AUTH_PASSWORD_FORMAT"
    AUTH_RATE_LIMITED = "AUTH_RATE_LIMITED"
    FORBIDDEN = "FORBIDDEN"

    # poc
    POC_DUPLICATE = "POC_DUPLICATE"
    POC_PARSE_ERROR = "POC_PARSE_ERROR"
    POC_VALIDATION_ERROR = "POC_VALIDATION_ERROR"
    POC_INVALID_STATUS_TRANSITION = "POC_INVALID_STATUS_TRANSITION"

    # data
    DATA_INTEGRITY = "DATA_INTEGRITY"

    # plugin
    PLUGIN_NOT_AVAILABLE = "PLUGIN_NOT_AVAILABLE"


# 错误码 → 默认 HTTP 状态
_ERROR_HTTP: dict[ErrorCode, int] = {
    ErrorCode.INTERNAL_ERROR: status.HTTP_500_INTERNAL_SERVER_ERROR,
    ErrorCode.REQUEST_INVALID: status.HTTP_422_UNPROCESSABLE_CONTENT,
    ErrorCode.NOT_FOUND: status.HTTP_404_NOT_FOUND,
    ErrorCode.CONFLICT: status.HTTP_409_CONFLICT,
    ErrorCode.AUTH_INVALID_CREDENTIALS: status.HTTP_401_UNAUTHORIZED,
    ErrorCode.AUTH_TOKEN_EXPIRED: status.HTTP_401_UNAUTHORIZED,
    ErrorCode.AUTH_TOKEN_INVALID: status.HTTP_401_UNAUTHORIZED,
    ErrorCode.AUTH_PASSWORD_FORMAT: status.HTTP_422_UNPROCESSABLE_CONTENT,
    ErrorCode.AUTH_RATE_LIMITED: status.HTTP_429_TOO_MANY_REQUESTS,
    ErrorCode.FORBIDDEN: status.HTTP_403_FORBIDDEN,
    ErrorCode.POC_DUPLICATE: status.HTTP_409_CONFLICT,
    ErrorCode.POC_PARSE_ERROR: status.HTTP_422_UNPROCESSABLE_CONTENT,
    ErrorCode.POC_VALIDATION_ERROR: status.HTTP_422_UNPROCESSABLE_CONTENT,
    ErrorCode.POC_INVALID_STATUS_TRANSITION: status.HTTP_409_CONFLICT,
    ErrorCode.DATA_INTEGRITY: status.HTTP_500_INTERNAL_SERVER_ERROR,
    ErrorCode.PLUGIN_NOT_AVAILABLE: status.HTTP_503_SERVICE_UNAVAILABLE,
}


class AppError(Exception):
    """业务异常基类，携带错误码 + 用户可读消息 + 细节数据 + 可选响应头。"""

    def __init__(
        self,
        code: ErrorCode,
        message: str | None = None,
        detail: dict | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.code = code
        self.message = message or code.value
        self.detail = detail or {}
        self.headers = headers or {}
        super().__init__(self.message)

    @property
    def http_status(self) -> int:
        return _ERROR_HTTP.get(self.code, status.HTTP_500_INTERNAL_SERVER_ERROR)


class RateLimitedError(AppError):
    """登录限流：携带 Retry-After 头，前端可据此提示冷却倒计时。"""

    def __init__(self, message: str, retry_after: int, detail: dict | None = None) -> None:
        super().__init__(
            ErrorCode.AUTH_RATE_LIMITED,
            message=message,
            detail=detail or {},
            headers={"Retry-After": str(retry_after), "X-RateLimit-Reset": str(retry_after)},
        )


class NotFoundError(AppError):
    def __init__(self, resource: str, ident: str) -> None:
        super().__init__(
            ErrorCode.NOT_FOUND,
            message=f"{resource} 不存在: {ident}",
            detail={"resource": resource, "id": ident},
        )


class PermissionDeniedError(AppError):
    def __init__(self, detail: str = "权限不足") -> None:
        super().__init__(ErrorCode.FORBIDDEN, message=detail)


def register_exception_handlers(app: FastAPI) -> None:
    """统一渲染：{code, message, data, request_id}。"""

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.http_status,
            headers=exc.headers or None,
            content={
                "code": exc.code.value,
                "message": exc.message,
                "data": exc.detail,
                "request_id": request.headers.get("X-Request-ID", ""),
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "code": ErrorCode.INTERNAL_ERROR.value,
                "message": "服务器内部错误",
                "data": {},
                "request_id": request.headers.get("X-Request-ID", ""),
            },
        )
