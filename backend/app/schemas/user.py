"""用户管理相关 Pydantic schema。"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class UserCreate(BaseModel):
    """创建用户请求体。"""

    username: str = Field(
        ..., min_length=3, max_length=64, pattern=r"^[a-zA-Z0-9_.-]+$", description="用户名"
    )
    email: str | None = Field(default=None, max_length=255, description="邮箱")
    password: str = Field(..., min_length=8, max_length=128, description="密码")
    role: str = Field(default="viewer", description="角色: viewer/editor/admin")


class UserUpdate(BaseModel):
    """更新用户请求体。"""

    email: str | None = None
    password: str | None = Field(default=None, min_length=8, max_length=128)
    role: str | None = None
    is_active: bool | None = None


class UserResponse(BaseModel):
    """用户响应体。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str | None = None
    role: str = "viewer"
    is_active: bool = True
    last_login_at: str | None = None
    created_at: str | None = None


class UserList(BaseModel):
    """用户列表。"""

    items: list[UserResponse]
    total: int


class RoleResponse(BaseModel):
    """角色响应体。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None = None
    permissions: str = "[]"
