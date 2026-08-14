"""依赖注入：DB 会话、当前用户、RBAC 守卫。"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy.orm import Session

from app.core.exceptions import AppError, ErrorCode, PermissionDeniedError
from app.core.security import Role, decode_token
from app.db.session import get_db
from app.models.user import User

DbSession = Annotated[Session, Depends(get_db)]


def _extract_token(authorization: str | None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise AppError(ErrorCode.AUTH_TOKEN_INVALID, "缺少 Bearer token")
    return authorization.split(" ", 1)[1].strip()


def get_current_user(
    db: DbSession,
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> User:
    """解析 access token → 加载用户。token 无效/过期/用户失效一律 401。"""
    token = _extract_token(authorization)
    data = decode_token(token, expected_type="access")
    user = db.get(User, int(data.sub))
    if user is None or not user.is_active:
        raise AppError(ErrorCode.AUTH_TOKEN_INVALID, "用户不存在或已停用")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*allowed: Role):
    """RBAC 守卫：角色不在允许集内 → 403。用法：require_roles(Role.ADMIN)。"""

    def dependency(user: CurrentUser) -> User:
        if user.role_name not in {r.value for r in allowed}:
            raise PermissionDeniedError(f"需要角色: {', '.join(r.value for r in allowed)}")
        return user

    return dependency


AdminUser = Annotated[User, Depends(require_roles(Role.ADMIN))]
