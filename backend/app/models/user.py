"""用户模型（RBAC）。"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.security import Role as RoleEnum
from app.db.base import Base, IntPKMixin, TimestampMixin


class User(Base, IntPKMixin, TimestampMixin):
    __tablename__ = "user"

    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    role_id: Mapped[int] = mapped_column(Integer, ForeignKey("role.id"), nullable=False, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_login_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    role: Mapped[Role] = relationship(back_populates="users")  # type: ignore[name-defined]

    @property
    def role_name(self) -> str:
        return self.role.name if self.role else RoleEnum.VIEWER.value


class Role(Base, IntPKMixin):
    """角色：viewer / editor / admin，permissions 为 JSON 权限集合。"""

    __tablename__ = "role"

    name: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    permissions: Mapped[dict] = mapped_column("permissions", String(2048), nullable=False, default="[]")

    users: Mapped[list[User]] = relationship(back_populates="role")
