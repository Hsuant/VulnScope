"""评论服务层（OOP 类）。

提供评论的 CRUD、树形加载、编辑窗口校验、软删除，所有写操作发布领域事件。
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.events import DomainEvent, event_bus
from app.core.exceptions import AppError, ErrorCode, NotFoundError, PermissionDeniedError
from app.models.comment import PocComment
from app.models.poc import Poc
from app.models.user import User
from app.schemas.comment import CommentCreate, CommentResponse, CommentUpdate


class CommentService:
    """评论服务。

    设计约束：
    - 最大嵌套深度 2 级（顶级 → 回复 → 回复的回复），超过时强制定级
    - 编辑窗口 30 分钟，超时不可编辑
    - 软删除：删除后保留占位，子回复仍然可见
    - 仅作者本人可编辑/删除自己的评论
    """

    MAX_DEPTH = 2
    EDIT_WINDOW_MINUTES = 30

    def __init__(self, db: Session, user_id: int):
        self._db = db
        self._user_id = user_id

    # ── CRUD ──────────────────────────────────────────────────────────────

    def create(self, poc_id: int, data: CommentCreate) -> PocComment:
        """发表评论或回复。

        Args:
            poc_id: POC ID
            data: 评论内容 + 父评论 ID（可选）

        Returns:
            创建的评论对象
        """
        # 校验 POC 存在
        poc = self._db.get(Poc, poc_id)
        if poc is None:
            raise NotFoundError("POC", str(poc_id))

        # 校验父评论存在且属于同一 POC
        if data.parent_id:
            parent = self._get_or_404(data.parent_id)
            if parent.poc_id != poc_id:
                raise AppError(ErrorCode.REQUEST_INVALID, "父评论不属于该 POC")
            # 计算父评论的深度：如果父评论本身是回复，则其深度为 1，否则为 0
            # 如果父评论已被删除，不允许回复
            if parent.deleted:
                raise AppError(ErrorCode.REQUEST_INVALID, "无法回复已删除的评论")

        comment = PocComment(
            poc_id=poc_id,
            user_id=self._user_id,
            content=data.content.strip(),
            parent_id=data.parent_id,
        )
        self._db.add(comment)
        self._db.commit()
        self._db.refresh(comment)

        # 发布事件
        event_bus.publish(
            DomainEvent(
                "poc.commented",
                str(poc_id),
                {
                    "comment_id": comment.id,
                    "user_id": self._user_id,
                    "parent_id": data.parent_id,
                },
            )
        )
        return comment

    def update(self, comment_id: int, data: CommentUpdate) -> PocComment:
        """编辑评论。

        Raises:
            PermissionDeniedError: 非作者或超时
        """
        comment = self._get_or_404(comment_id)
        self._check_owner(comment)

        # 已删除的评论不可编辑
        if comment.deleted:
            raise AppError(ErrorCode.REQUEST_INVALID, "无法编辑已删除的评论")

        # 编辑窗口检查
        elapsed = (dt.datetime.now(dt.timezone.utc) - comment.created_at).total_seconds()
        if elapsed > self.EDIT_WINDOW_MINUTES * 60:
            raise PermissionDeniedError(
                f"超过编辑窗口时间（{self.EDIT_WINDOW_MINUTES} 分钟），如需修改请删除后重新评论"
            )

        comment.content = data.content.strip()
        comment.edited = True
        self._db.commit()
        self._db.refresh(comment)
        return comment

    def delete(self, comment_id: int) -> None:
        """删除评论（软删除：保留占位，子回复仍然可见）。

        如果评论有子回复，保留占位文本「该评论已被删除」；
        如果没有子回复，硬删除。
        """
        comment = self._get_or_404(comment_id)
        self._check_owner(comment)

        # 检查是否有子回复
        has_replies = (
            self._db.scalar(
                select(PocComment.id)
                .where(
                    PocComment.parent_id == comment_id,
                    PocComment.deleted == False,  # noqa: E712
                )
                .limit(1)
            )
            is not None
        )

        if has_replies:
            comment.content = "该评论已被删除"
            comment.deleted = True
            comment.edited = False
        else:
            self._db.delete(comment)

        self._db.commit()

    # ── 查询 ──────────────────────────────────────────────────────────────

    def list_for_poc(self, poc_id: int) -> list[CommentResponse]:
        """获取 POC 所有评论（顶级评论 + 嵌套回复，按时间排序）。

        返回树形结构：顶级评论下挂 replies，每层递归下挂子 replies。
        """
        # 校验 POC 存在
        poc = self._db.get(Poc, poc_id)
        if poc is None:
            raise NotFoundError("POC", str(poc_id))

        # 获取所有顶级评论
        top_comments = self._db.scalars(
            select(PocComment)
            .where(PocComment.poc_id == poc_id, PocComment.parent_id.is_(None))
            .order_by(PocComment.created_at.asc())
        ).all()

        return [self._build_tree(c) for c in top_comments]

    # ── 内部辅助 ──────────────────────────────────────────────────────────

    def _build_tree(self, comment: PocComment) -> CommentResponse:
        """递归构建评论树。"""
        user = self._db.get(User, comment.user_id)
        username = user.username if user else "已删除用户"

        # 软删除的评论不展示子回复的内容（但保留结构）
        replies = []
        if not comment.deleted:
            replies = [self._build_tree(reply) for reply in (comment.replies or [])]

        return CommentResponse(
            id=comment.id,
            poc_id=comment.poc_id,
            user_id=comment.user_id,
            username=username,
            content=comment.content if not comment.deleted else "该评论已被删除",
            parent_id=comment.parent_id,
            edited=comment.edited,
            deleted=comment.deleted,
            created_at=comment.created_at,
            updated_at=comment.updated_at,
            replies=replies,
        )

    def _get_or_404(self, comment_id: int) -> PocComment:
        comment = self._db.get(PocComment, comment_id)
        if comment is None:
            raise NotFoundError("Comment", str(comment_id))
        return comment

    def _check_owner(self, comment: PocComment) -> None:
        """校验评论归属。"""
        if comment.user_id != self._user_id:
            raise PermissionDeniedError("只能操作自己的评论")
