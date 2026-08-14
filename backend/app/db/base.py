"""SQLAlchemy 声明式基类与公共列。"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import DateTime, Integer, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """所有 ORM 模型的公共基类。"""


class TimestampMixin:
    """created_at / updated_at 公共列，跨方言兼容。"""

    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=text("CURRENT_TIMESTAMP"),
    )


class IntPKMixin:
    """自增主键（Integer，跨方言自动选择 AUTOINCREMENT 策略）。"""

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)


def generate_uuid4() -> str:
    import uuid

    return str(uuid.uuid4())
