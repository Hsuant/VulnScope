"""用户管理 API 路由（仅 admin 角色可访问）。"""

from __future__ import annotations

from fastapi import APIRouter, Query, Request

from app.api.deps import AdminUser, DbSession
from app.schemas.common import ok
from app.schemas.user import UserCreate, UserUpdate
from app.services import user_service

router = APIRouter(prefix="/users", tags=["users"])


@router.get("")
def list_users(
    request: Request,
    db: DbSession,
    user: AdminUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> dict:
    """获取用户列表（需要 admin 角色）。"""
    items, total = user_service.list_users(db, page=page, page_size=page_size)
    return ok({"items": items, "total": total}, request)


@router.get("/roles")
def list_roles(
    request: Request,
    db: DbSession,
    user: AdminUser,
) -> dict:
    """获取角色列表（需要 admin 角色）。"""
    roles = user_service.list_roles(db)
    return ok(roles, request)


@router.get("/{user_id}")
def get_user(
    request: Request,
    db: DbSession,
    user: AdminUser,
    user_id: int,
) -> dict:
    """获取用户详情（需要 admin 角色）。"""
    user_data = user_service.get_user(db, user_id)
    return ok(user_data, request)


@router.post("", status_code=200)
def create_user(
    request: Request,
    db: DbSession,
    body: UserCreate,
    user: AdminUser,
) -> dict:
    """创建用户（需要 admin 角色）。"""
    new_user = user_service.create_user(db, body)
    return ok(
        {
            "id": new_user.id,
            "username": new_user.username,
            "email": new_user.email,
            "role": new_user.role_name,
            "is_active": new_user.is_active,
        },
        request,
    )


@router.put("/{user_id}")
def update_user(
    request: Request,
    db: DbSession,
    user_id: int,
    body: UserUpdate,
    user: AdminUser,
) -> dict:
    """更新用户信息（需要 admin 角色）。"""
    updated = user_service.update_user(db, user_id, body)
    return ok(
        {
            "id": updated.id,
            "username": updated.username,
            "email": updated.email,
            "role": updated.role_name,
            "is_active": updated.is_active,
        },
        request,
    )


@router.delete("/{user_id}")
def delete_user(
    request: Request,
    db: DbSession,
    user: AdminUser,
    user_id: int,
) -> dict:
    """删除用户（需要 admin 角色，不能删除内置管理员）。"""
    user_service.delete_user(db, user_id)
    return ok({"deleted": True}, request)
