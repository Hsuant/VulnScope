"""通知模型：站内信通知，记录订阅匹配触发的推送内容。"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IntPKMixin, TimestampMixin


class Notification(Base, IntPKMixin, TimestampMixin):
    """订阅触发的通知记录（站内信）。

    当 POC 创建/更新匹配到用户的订阅规则时，生成一条通知。
    """

    __tablename__ = "notification"

    __table_args__ = (
        Index("ix_notification_user_read", "user_id", "is_read"),
        Index("ix_notification_user_created", "user_id", "created_at"),
        {"sqlite_autoincrement": True},
    )

    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("user.id"), nullable=False, index=True
    )
    notification_type: Mapped[str] = mapped_column(
        String(32), nullable=False, comment="通知类型: new_poc / poc_updated"
    )
    title: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="通知标题"
    )
    content: Mapped[str] = mapped_column(
        Text, nullable=False, default="", comment="通知正文摘要"
    )
    sub_type: Mapped[str] = mapped_column(
        String(32), nullable=False, comment="匹配的订阅类型: cve / vendor / tag"
    )
    sub_target: Mapped[str] = mapped_column(
        String(128), nullable=False, comment="匹配的订阅目标值"
    )
    ref_type: Mapped[str] = mapped_column(
        String(32), nullable=False, default="poc", comment="关联资源类型: poc"
    )
    ref_id: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="关联资源 ID"
    )
    is_read: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, comment="是否已读"
    )
    read_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="阅读时间"
    )
