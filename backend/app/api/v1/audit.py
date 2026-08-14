"""审计日志 API 路由。"""

from __future__ import annotations

from fastapi import APIRouter, Query, Request

from app.api.deps import AdminUser, DbSession
from app.schemas.common import ok
from app.services import audit_service

router = APIRouter(prefix="/audit-logs", tags=["audit-logs"])


@router.get("")
def list_audit_logs(
    request: Request,
    db: DbSession,
    user: AdminUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    action: str | None = Query(default=None, description="按操作类型筛选"),
    resource_type: str | None = Query(default=None, description="按资源类型筛选"),
    user_id: int | None = Query(default=None, description="按用户 ID 筛选"),
) -> dict:
    """分页查询审计日志（需要 admin 角色）。

    记录所有写操作（创建/更新/删除/状态变更），含操作前/后摘要和 IP 地址。
    """
    items, total = audit_service.list_audit_logs(
        db,
        page=page,
        page_size=page_size,
        action=action,
        resource_type=resource_type,
        user_id=user_id,
    )
    return ok({"items": items, "total": total}, request)
