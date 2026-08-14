"""认证相关 Pydantic schema。"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator


class LoginRequest(BaseModel):
    """登录请求体。"""

    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class RefreshRequest(BaseModel):
    """Token 刷新请求体。"""

    refresh_token: str


class ProfileUpdate(BaseModel):
    """个人信息修改请求体。"""

    email: str | None = Field(default=None, max_length=255, description="新邮箱")
    password: str | None = Field(default=None, min_length=8, max_length=128, description="新密码")


class TokenResponse(BaseModel):
    """Token 响应体。"""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    """用户信息响应体。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str | None = None
    role: str
    is_active: bool

    @field_validator("role", mode="before")
    @classmethod
    def extract_role_name(cls, v: object) -> str:
        """从 SQLAlchemy Role 对象中提取角色名。"""
        if isinstance(v, str):
            return v
        if hasattr(v, "name"):
            return str(v.name)
        return str(v)


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=64, pattern=r"^[a-zA-Z0-9_.-]+$")
    email: str | None = Field(default=None, max_length=255)
    password: str = Field(min_length=8, max_length=128)
    role: str = "viewer"


class LoginResponse(TokenResponse):
    user: UserOut
