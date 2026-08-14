"""审计日志服务层。"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.poc import AuditLog
from app.models.user import User


def list_audit_logs(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 20,
    action: str | None = None,
    resource_type: str | None = None,
    user_id: int | None = None,
) -> tuple[list[dict], int]:
    """分页查询审计日志，含用户信息。"""
    query = select(AuditLog)

    if action:
        query = query.where(AuditLog.action == action)
    if resource_type:
        query = query.where(AuditLog.resource_type == resource_type)
    if user_id:
        query = query.where(AuditLog.user_id == user_id)

    # 总数
    count_query = (
        select(func.count()).select_from(AuditLog).where(query.whereclause)
        if query.whereclause is not None
        else select(func.count()).select_from(AuditLog)
    )
    total = db.scalar(count_query) or 0

    # 分页
    offset = (page - 1) * page_size
    logs = db.scalars(query.order_by(AuditLog.created_at.desc()).offset(offset).limit(page_size)).all()

    result = []
    for log in logs:
        username = ""
        if log.user_id:
            user = db.get(User, log.user_id)
            if user:
                username = user.username
        result.append(
            {
                "id": log.id,
                "user_id": log.user_id,
                "username": username,
                "action": log.action,
                "resource_type": log.resource_type,
                "resource_id": log.resource_id,
                "detail": log.detail,
                "ip": log.ip,
                "created_at": log.created_at.isoformat() if log.created_at else None,
            }
        )

    return result, total
