"""安全工具：bcrypt 密码哈希 + JWT 签发/校验（PyJWT）+ 三角色 RBAC。"""

from __future__ import annotations

import datetime as dt
from enum import Enum

import bcrypt
import jwt
from pydantic import BaseModel

from app.core.config import settings
from app.core.exceptions import AppError, ErrorCode


class Role(str, Enum):
    """RBAC 三角色。"""

    VIEWER = "viewer"  # 只读
    EDITOR = "editor"  # 增删改
    ADMIN = "admin"  # 系统管理


# ── 密码哈希（bcrypt，含随机盐） ──────────────────────────────────────


def hash_password(plain: str) -> str:
    """对明文密码进行 bcrypt 哈希，含随机盐。

    Args:
        plain: 明文密码，长度至少 8 位。

    Returns:
        bcrypt 哈希字符串（含盐，可直接存入数据库）。

    Raises:
        AppError: 密码长度不足 8 位时抛出 AUTH_PASSWORD_FORMAT。
    """
    salt = bcrypt.gensalt(rounds=settings.PASSWORD_BCRYPT_ROUNDS)
    return bcrypt.hashpw(plain.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """校验明文密码与 bcrypt 哈希是否匹配。

    Args:
        plain: 明文密码。
        hashed: 数据库中存储的 bcrypt 哈希。

    Returns:
        匹配返回 True，否则返回 False。哈希格式异常时也返回 False。
    """
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


# ── JWT ──────────────────────────────────────────────────────────────

_TOKEN_TYPES = {"access", "refresh"}


class TokenData(BaseModel):
    sub: str  # user_id
    username: str
    role: str
    typ: str  # access | refresh
    exp: int


def create_token(
    user_id: int,
    username: str,
    role: str,
    token_type: str = "access",
    expires_delta: dt.timedelta | None = None,
) -> str:
    """签发 JWT token。

    Args:
        user_id: 用户 ID，存入 sub 声明。
        username: 用户名。
        role: 角色名。
        token_type: token 类型，access 或 refresh。
        expires_delta: 过期时间，默认按配置使用 access 30 分钟 / refresh 7 天。

    Returns:
        JWT 签名后的字符串。

    Raises:
        ValueError: token_type 不合法时抛出。
    """
    if token_type not in _TOKEN_TYPES:
        raise ValueError(f"未知 token 类型: {token_type}")
    if token_type == "access":
        delta = expires_delta or dt.timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    else:
        delta = expires_delta or dt.timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    payload = {
        "sub": str(user_id),
        "username": username,
        "role": role,
        "typ": token_type,
        "iat": dt.datetime.now(dt.timezone.utc),
        "exp": dt.datetime.now(dt.timezone.utc) + delta,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str, expected_type: str = "access") -> TokenData:
    """校验 JWT 签名、过期、token 类型。失败统一抛 401。"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except jwt.ExpiredSignatureError as e:
        raise AppError(ErrorCode.AUTH_TOKEN_EXPIRED, "token 已过期") from e
    except (jwt.InvalidTokenError, jwt.InvalidSignatureError) as e:
        raise AppError(ErrorCode.AUTH_TOKEN_INVALID, "token 无效") from e

    if payload.get("typ") != expected_type:
        raise AppError(ErrorCode.AUTH_TOKEN_INVALID, f"token 类型不符，期望 {expected_type}")

    try:
        data = TokenData(
            sub=str(payload["sub"]),
            username=str(payload["username"]),
            role=str(payload["role"]),
            typ=str(payload["typ"]),
            exp=int(payload["exp"]),
        )
    except KeyError as e:
        raise AppError(ErrorCode.AUTH_TOKEN_INVALID, "token 缺少必要声明") from e
    return data


def issue_token_pair(user_id: int, username: str, role: str) -> dict[str, str]:
    """签发 access + refresh token 对。

    Args:
        user_id: 用户 ID。
        username: 用户名。
        role: 角色名。

    Returns:
        包含 access_token、refresh_token、token_type 的字典。
    """
    return {
        "access_token": create_token(user_id, username, role, "access"),
        "refresh_token": create_token(user_id, username, role, "refresh"),
        "token_type": "bearer",
    }
