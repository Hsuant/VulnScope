"""POC 评论/讨论模型：支持树形回复（两级嵌套），便于团队协作审核。"""

from __future__ import annotations

from sqlalchemy import BigInteger, Boolean, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, IntPKMixin, TimestampMixin


class PocComment(Base, IntPKMixin, TimestampMixin):
    """POC 评论/讨论（支持树形回复）。

    设计约束：
    - 最大嵌套深度 2 级（顶级 → 回复 → 回复的回复），超过时强制定级到 2 级
    - 编辑窗口 30 分钟，超时不可编辑
    - 删除后保留占位「该评论已被删除」，子回复仍然可见
    - 仅作者本人可编辑/删除自己的评论
    """

    __tablename__ = "poc_comment"

    __table_args__ = {"sqlite_autoincrement": True}

    poc_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("poc.id"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("user.id"), nullable=False, index=True
    )
    parent_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("poc_comment.id"), nullable=True, index=True,
        comment="父评论 ID，NULL 表示顶级评论",
    )
    content: Mapped[str] = mapped_column(
        Text, nullable=False, comment="评论内容（纯文本，最大 10000 字符）"
    )
    edited: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, comment="是否已编辑"
    )
    deleted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, comment="是否已删除（软删除，保留占位）"
    )

    # 关联
    poc: Mapped["Poc"] = relationship(back_populates="comments")  # noqa: F821
    user: Mapped["User"] = relationship(lazy="joined")  # noqa: F821
    replies: Mapped[list[PocComment]] = relationship(
        back_populates="parent",
        cascade="all, delete-orphan",
        foreign_keys=[parent_id],
        lazy="selectin",
        order_by=lambda: PocComment.created_at.asc(),
    )
    parent: Mapped[PocComment | None] = relationship(
        back_populates="replies",
        remote_side="PocComment.id",
        lazy="joined",
    )