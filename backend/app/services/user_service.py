"""用户管理服务层。"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import AppError, ErrorCode, NotFoundError
from app.core.security import Role, hash_password
from app.core.timeutil import iso_utc
from app.models.user import Role as RoleModel
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate


def list_users(db: Session, *, page: int = 1, page_size: int = 20) -> tuple[list[dict], int]:
    """分页查询用户列表。"""
    query = select(User)
    total = db.scalar(select(func.count()).select_from(User)) or 0

    offset = (page - 1) * page_size
    users = db.scalars(query.order_by(User.created_at.desc()).offset(offset).limit(page_size)).all()

    result = [_user_to_dict(u) for u in users]
    return result, total


def get_user(db: Session, user_id: int) -> dict:
    """获取用户详情。"""
    user = db.get(User, user_id)
    if user is None:
        raise NotFoundError("用户", str(user_id))
    return _user_to_dict(user)


def create_user(db: Session, data: UserCreate) -> User:
    """创建用户（检查用户名唯一性）。"""
    existing = db.scalar(select(User).where(User.username == data.username))
    if existing:
        raise AppError(ErrorCode.CONFLICT, f"用户名 '{data.username}' 已存在")

    if data.email:
        existing_email = db.scalar(select(User).where(User.email == data.email))
        if existing_email:
            raise AppError(ErrorCode.CONFLICT, f"邮箱 '{data.email}' 已存在")

    # 查找角色
    role = db.scalar(select(RoleModel).where(RoleModel.name == data.role))
    if role is None:
        # 使用默认 viewer 角色
        role = db.scalar(select(RoleModel).where(RoleModel.name == Role.VIEWER.value))
        if role is None:
            raise AppError(ErrorCode.INTERNAL_ERROR, "默认角色不存在，请先执行种子数据初始化")

    user = User(
        username=data.username,
        email=data.email,
        password_hash=hash_password(data.password),
        role_id=role.id,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_user(db: Session, user_id: int, data: UserUpdate) -> User:
    """更新用户信息。"""
    user = db.get(User, user_id)
    if user is None:
        raise NotFoundError("用户", str(user_id))

    update_data = data.model_dump(exclude_unset=True)

    # 检查邮箱唯一性
    if "email" in update_data and update_data["email"] and update_data["email"] != user.email:
        existing = db.scalar(select(User).where(User.email == update_data["email"], User.id != user_id))
        if existing:
            raise AppError(ErrorCode.CONFLICT, f"邮箱 '{update_data['email']}' 已被使用")

    # 处理密码
    if "password" in update_data and update_data["password"]:
        update_data["password_hash"] = hash_password(update_data.pop("password"))

    # 处理角色
    if "role" in update_data and update_data["role"]:
        role_name = update_data.pop("role")
        role = db.scalar(select(RoleModel).where(RoleModel.name == role_name))
        if role is None:
            raise AppError(ErrorCode.REQUEST_INVALID, f"角色 '{role_name}' 不存在")
        update_data["role_id"] = role.id

    for field, value in update_data.items():
        if value is not None:
            setattr(user, field, value)

    db.commit()
    db.refresh(user)
    return user


def delete_user(db: Session, user_id: int) -> None:
    """删除用户。"""
    user = db.get(User, user_id)
    if user is None:
        raise NotFoundError("用户", str(user_id))
    if user.username == "admin":
        raise AppError(ErrorCode.FORBIDDEN, "不能删除内置管理员账号")
    db.delete(user)
    db.commit()


def list_roles(db: Session) -> list[dict]:
    """获取所有角色列表。"""
    roles = db.scalars(select(RoleModel).order_by(RoleModel.id)).all()
    return [_role_to_dict(r) for r in roles]


def _user_to_dict(user: User) -> dict:
    """将 User ORM 对象转为字典。"""
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role_name,
        "is_active": user.is_active,
        "last_login_at": iso_utc(user.last_login_at),
        "created_at": iso_utc(user.created_at) if hasattr(user, "created_at") else None,
    }


def _role_to_dict(role: RoleModel) -> dict:
    """将 Role ORM 对象转为字典。"""
    return {
        "id": role.id,
        "name": role.name,
        "description": role.description,
        "permissions": role.permissions,
    }
