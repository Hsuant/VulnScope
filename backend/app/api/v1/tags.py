"""标签管理 API 路由。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request

from app.api.deps import CurrentUser, DbSession, require_roles
from app.core.security import Role
from app.models.user import User
from app.schemas.common import ok
from app.schemas.tag import TagCreate, TagUpdate
from app.services import tag_service

router = APIRouter(prefix="/tags", tags=["tags"])


@router.get("")
def list_tags(
    request: Request,
    db: DbSession,
    user: CurrentUser,
    namespace: str | None = Query(default=None, description="按命名空间筛选"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
) -> dict:
    """获取标签列表（含每个标签的 POC 关联数）。"""
    items, total = tag_service.list_tags(db, namespace=namespace, page=page, page_size=page_size)
    return ok({"items": items, "total": total}, request)


@router.get("/namespaces")
def list_namespaces(
    request: Request,
    db: DbSession,
    user: CurrentUser,
) -> dict:
    """获取所有标签命名空间列表。"""
    namespaces = tag_service.list_namespaces(db)
    return ok(namespaces, request)


@router.get("/{tag_id}")
def get_tag(
    request: Request,
    db: DbSession,
    user: CurrentUser,
    tag_id: int,
) -> dict:
    """获取标签详情（含 POC 关联数）。"""
    tag = tag_service.get_tag(db, tag_id)
    return ok(tag, request)


@router.post("", status_code=200)
def create_tag(
    request: Request,
    db: DbSession,
    body: TagCreate,
    user: User = Depends(require_roles(Role.EDITOR, Role.ADMIN)),
) -> dict:
    """创建标签（需要 editor 或 admin 角色）。"""
    tag = tag_service.create_tag(db, body)
    poc_count = 0
    return ok(
        {
            "id": tag.id,
            "namespace": tag.namespace,
            "name": tag.name,
            "color": tag.color,
            "description": tag.description,
            "poc_count": poc_count,
        },
        request,
    )


@router.put("/{tag_id}")
def update_tag(
    request: Request,
    db: DbSession,
    tag_id: int,
    body: TagUpdate,
    user: User = Depends(require_roles(Role.EDITOR, Role.ADMIN)),
) -> dict:
    """更新标签（需要 editor 或 admin 角色）。"""
    tag = tag_service.update_tag(db, tag_id, body)
    poc_count = 0
    return ok(
        {
            "id": tag.id,
            "namespace": tag.namespace,
            "name": tag.name,
            "color": tag.color,
            "description": tag.description,
            "poc_count": poc_count,
        },
        request,
    )


@router.delete("/{tag_id}")
def delete_tag(
    request: Request,
    db: DbSession,
    tag_id: int,
    user: User = Depends(require_roles(Role.EDITOR, Role.ADMIN)),
) -> dict:
    """删除标签（需要 editor 或 admin 角色）。"""
    tag_service.delete_tag(db, tag_id)
    return ok({"deleted": True}, request)
