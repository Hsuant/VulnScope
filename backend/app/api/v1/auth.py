"""认证路由：登录 / 刷新 / 当前用户 / 个人信息修改。"""

from __future__ import annotations

from fastapi import APIRouter, Request

from app.api.deps import CurrentUser, DbSession
from app.core.security import issue_token_pair
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    ProfileUpdate,
    RefreshRequest,
    TokenResponse,
    UserOut,
)
from app.schemas.common import ok
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
def login(request: Request, body: LoginRequest, db: DbSession) -> dict:
    user = auth_service.authenticate(db, body.username, body.password)
    tokens = issue_token_pair(user.id, user.username, user.role_name)
    resp = LoginResponse(**tokens, user=UserOut.model_validate(user))
    return ok(resp.model_dump(), request)


@router.post("/refresh")
def refresh(request: Request, body: RefreshRequest, db: DbSession) -> dict:
    tokens = auth_service.refresh_tokens(db, body.refresh_token)
    return ok(TokenResponse(**tokens).model_dump(), request)


@router.get("/me")
def me(request: Request, user: CurrentUser) -> dict:
    return ok(UserOut.model_validate(user).model_dump(), request)


@router.put("/profile")
def update_profile(request: Request, db: DbSession, user: CurrentUser, body: ProfileUpdate) -> dict:
    """修改个人信息（邮箱、密码）。"""
    updated = auth_service.update_profile(db, user.id, body)
    return ok(UserOut.model_validate(updated).model_dump(), request)
