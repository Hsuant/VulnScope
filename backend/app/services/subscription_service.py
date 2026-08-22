"""订阅服务层（OOP 类）。

提供订阅规则的 CRUD 操作，供订阅管理页面使用。
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import AppError, ErrorCode, NotFoundError, PermissionDeniedError
from app.models.poc import Tag, Vendor
from app.models.subscription import Subscription
from app.schemas.subscription import SubscriptionCreate, SubscriptionUpdate


class SubscriptionService:
    """订阅服务：CRUD。"""

    VALID_TYPES = {"cve", "vendor", "tag"}
    MAX_PAGE_SIZE = 100

    def __init__(self, db: Session, user_id: int):
        self._db = db
        self._user_id = user_id

    # ── CRUD ──────────────────────────────────────────────────────────────

    def create(self, data: SubscriptionCreate) -> Subscription:
        """创建订阅规则。"""
        if data.sub_type not in self.VALID_TYPES:
            raise AppError(
                ErrorCode.REQUEST_INVALID,
                f"不支持的订阅类型: {data.sub_type}，可选: {', '.join(sorted(self.VALID_TYPES))}",
            )

        # 校验目标存在
        if data.sub_type == "tag":
            try:
                tag_id = int(data.target_id)
            except ValueError:
                raise AppError(ErrorCode.REQUEST_INVALID, "标签订阅的 target_id 须为标签 ID 数字") from None
            tag = self._db.get(Tag, tag_id)
            if tag is None:
                raise NotFoundError("Tag", data.target_id)

        # 重复检查
        existing = self._db.scalar(
            select(Subscription).where(
                Subscription.user_id == self._user_id,
                Subscription.sub_type == data.sub_type,
                Subscription.target_id == data.target_id,
            )
        )
        if existing:
            raise AppError(
                ErrorCode.CONFLICT,
                f"已存在相同订阅规则: {data.sub_type} / {data.target_id}",
            )

        sub = Subscription(
            user_id=self._user_id,
            sub_type=data.sub_type,
            target_id=data.target_id,
            notify_on_update=data.notify_on_update,
            notify_on_new=data.notify_on_new,
        )
        self._db.add(sub)
        self._db.commit()
        self._db.refresh(sub)
        return sub

    def update(self, sub_id: int, data: SubscriptionUpdate) -> Subscription:
        """更新订阅通知偏好。"""
        sub = self._get_or_404(sub_id)
        if sub.user_id != self._user_id:
            raise PermissionDeniedError("只能编辑自己的订阅")

        for field, val in data.model_dump(exclude_unset=True).items():
            setattr(sub, field, val)
        self._db.commit()
        self._db.refresh(sub)
        return sub

    def delete(self, sub_id: int) -> None:
        """取消订阅。"""
        sub = self._get_or_404(sub_id)
        if sub.user_id != self._user_id:
            raise PermissionDeniedError("只能取消自己的订阅")
        self._db.delete(sub)
        self._db.commit()

    def list_mine(self, page: int = 1, page_size: int = 20) -> tuple[list[Subscription], int]:
        """分页查询我的订阅列表。"""
        if page_size > self.MAX_PAGE_SIZE:
            page_size = self.MAX_PAGE_SIZE

        base = select(Subscription).where(Subscription.user_id == self._user_id)
        total = (
            self._db.scalar(
                select(func.count()).select_from(Subscription).where(Subscription.user_id == self._user_id)
            )
            or 0
        )
        items = self._db.scalars(
            base.order_by(Subscription.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        ).all()
        return list(items), total

    def get_target_display(self, sub: Subscription) -> str | None:
        """获取订阅目标的展示名称。"""
        if sub.sub_type == "cve":
            return sub.target_id  # CVE 编号本身就是展示名
        elif sub.sub_type == "vendor":
            vendor = self._db.scalar(select(Vendor).where(Vendor.slug == sub.target_id))
            return vendor.name if vendor else sub.target_id
        elif sub.sub_type == "tag":
            try:
                tag = self._db.get(Tag, int(sub.target_id))
                return f"{tag.namespace}:{tag.name}" if tag else sub.target_id
            except (ValueError, TypeError):
                return sub.target_id
        return sub.target_id

    # ── 内部辅助 ──────────────────────────────────────────────────────────

    def _get_or_404(self, sub_id: int) -> Subscription:
        sub = self._db.get(Subscription, sub_id)
        if sub is None:
            raise NotFoundError("Subscription", str(sub_id))
        return sub
