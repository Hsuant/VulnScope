"""认证服务：登录、刷新、种子账号创建。"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import AppError, ErrorCode
from app.core.security import (
    Role,
    decode_token,
    hash_password,
    issue_token_pair,
    verify_password,
)
from app.models.user import Role as RoleModel
from app.models.user import User
from app.schemas.auth import ProfileUpdate


def authenticate(db: Session, username: str, password: str) -> User:
    """校验用户名密码；失败统一 401，不区分"用户不存在"与"密码错误"。"""
    user = db.scalar(select(User).where(User.username == username))
    if user is None or not verify_password(password, user.password_hash):
        raise AppError(ErrorCode.AUTH_INVALID_CREDENTIALS, "用户名或密码错误")
    if not user.is_active:
        raise AppError(ErrorCode.AUTH_INVALID_CREDENTIALS, "账号已停用")

    user.last_login_at = dt.datetime.now(dt.timezone.utc)
    db.commit()
    return user


def refresh_tokens(db: Session, refresh_token: str) -> dict[str, str]:
    """校验 refresh token → 签发新 token 对。"""
    data = decode_token(refresh_token, expected_type="refresh")
    user = db.get(User, int(data.sub))
    if user is None or not user.is_active:
        raise AppError(ErrorCode.AUTH_TOKEN_INVALID, "用户不存在或已停用")
    return issue_token_pair(user.id, user.username, user.role_name)


def _ensure_role(db: Session, name: str, description: str) -> RoleModel:
    role = db.scalar(select(RoleModel).where(RoleModel.name == name))
    if role is None:
        role = RoleModel(name=name, description=description)
        db.add(role)
        db.flush()
    return role


def seed_roles(db: Session) -> None:
    """初始化三个内置角色（幂等）。"""
    roles = {
        Role.VIEWER.value: "只读：查看 POC、标签、插件状态",
        Role.EDITOR.value: "编辑：POC 增删改、导入导出、标签管理",
        Role.ADMIN.value: "系统管理：用户、角色、审计日志",
    }
    for name, description in roles.items():
        _ensure_role(db, name, description)
    db.commit()


def seed_admin(db: Session) -> None:
    """创建默认管理员（仅当 admin 不存在，幂等）。"""
    admin_role = _ensure_role(db, Role.ADMIN.value, "")
    existing = db.scalar(select(User).where(User.username == settings.SEED_ADMIN_USERNAME))
    if existing is None:
        user = User(
            username=settings.SEED_ADMIN_USERNAME,
            email=settings.SEED_ADMIN_EMAIL,
            password_hash=hash_password(settings.SEED_ADMIN_PASSWORD),
            role_id=admin_role.id,
        )
        db.add(user)
        db.commit()


def update_profile(db: Session, user_id: int, data: ProfileUpdate) -> User:
    """修改个人信息（邮箱、密码）。"""
    user = db.get(User, user_id)
    if user is None:
        raise AppError(ErrorCode.NOT_FOUND, "用户不存在")

    update_data = data.model_dump(exclude_unset=True)

    # 检查邮箱唯一性
    if "email" in update_data and update_data["email"] and update_data["email"] != user.email:
        existing = db.scalar(select(User).where(User.email == update_data["email"], User.id != user_id))
        if existing:
            raise AppError(ErrorCode.CONFLICT, "该邮箱已被其他账号使用")

    if "password" in update_data and update_data["password"]:
        update_data["password_hash"] = hash_password(update_data.pop("password"))

    for field, value in update_data.items():
        if value is not None:
            setattr(user, field, value)

    db.commit()
    db.refresh(user)
    return user
