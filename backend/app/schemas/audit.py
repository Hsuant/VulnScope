"""审计日志相关 Pydantic schema。"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class AuditLogResponse(BaseModel):
    """审计日志响应体。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int | None = None
    username: str = ""
    action: str
    resource_type: str
    resource_id: str | None = None
    detail: dict[str, Any] | None = None
    ip: str | None = None
    created_at: str | None = None


class AuditLogList(BaseModel):
    """审计日志列表（含分页）。"""

    items: list[AuditLogResponse]
    total: int
