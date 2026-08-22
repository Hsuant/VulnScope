"""订阅模型：按 CVE / 厂商 / 标签订阅更新通知。"""

from __future__ import annotations

from sqlalchemy import BigInteger, Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IntPKMixin, TimestampMixin


class Subscription(Base, IntPKMixin, TimestampMixin):
    """订阅规则（按 CVE / 厂商 / 标签订阅）。

    用户订阅一个「主题」，当该主题下有新 POC 导入或 POC 更新时，
    系统可生成通知推送（v1 仅存储规则，v1.5 实现通知推送）。
    """

    __tablename__ = "subscription"

    __table_args__ = (
        UniqueConstraint("user_id", "sub_type", "target_id", name="uq_subscription_user_type_target"),
        {"sqlite_autoincrement": True},
    )

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("user.id"), nullable=False, index=True
    )
    sub_type: Mapped[str] = mapped_column(
        String(32), nullable=False, index=True, comment="订阅类型: cve / vendor / tag"
    )
    target_id: Mapped[str] = mapped_column(
        String(128), nullable=False, comment="目标标识: CVE编号 / 厂商slug / 标签ID(字符串)"
    )
    notify_on_update: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, comment="POC 更新时通知"
    )
    notify_on_new: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, comment="新 POC 导入时通知"
    )