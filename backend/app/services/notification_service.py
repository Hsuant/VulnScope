"""Notification service layer (OOP class): CRUD, unread count, mark read."""

from __future__ import annotations

import datetime as dt

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, PermissionDeniedError
from app.models.notification import Notification


class NotificationService:
    """Notification service: list, unread count, mark read."""

    MAX_PAGE_SIZE = 100

    def __init__(self, db: Session, user_id: int) -> None:
        self._db = db
        self._user_id = user_id

    def list_mine(
        self, page: int = 1, page_size: int = 20, unread_only: bool = False
    ) -> tuple[list[Notification], int, int]:
        if page_size > self.MAX_PAGE_SIZE:
            page_size = self.MAX_PAGE_SIZE

        base = select(Notification).where(Notification.user_id == self._user_id)
        if unread_only:
            base = base.where(Notification.is_read == False)  # noqa: E712

        total = (
            self._db.scalar(
                select(func.count()).select_from(Notification).where(Notification.user_id == self._user_id)
            )
            or 0
        )
        unread_count = (
            self._db.scalar(
                select(func.count())
                .select_from(Notification)
                .where(
                    Notification.user_id == self._user_id,
                    Notification.is_read == False,  # noqa: E712
                )
            )
            or 0
        )

        items = self._db.scalars(
            base.order_by(Notification.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        ).all()

        return list(items), total, unread_count

    def unread_count(self) -> int:
        return (
            self._db.scalar(
                select(func.count())
                .select_from(Notification)
                .where(
                    Notification.user_id == self._user_id,
                    Notification.is_read == False,  # noqa: E712
                )
            )
            or 0
        )

    def mark_read(self, notif_id: int) -> Notification:
        notif = self._get_or_404(notif_id)
        if notif.user_id != self._user_id:
            raise PermissionDeniedError("can only operate on own notifications")
        notif.is_read = True
        notif.read_at = dt.datetime.now(dt.timezone.utc)
        self._db.commit()
        self._db.refresh(notif)
        return notif

    def mark_all_read(self) -> int:
        now = dt.datetime.now(dt.timezone.utc)
        count = (
            self._db.query(Notification)
            .filter(
                Notification.user_id == self._user_id,
                Notification.is_read == False,  # noqa: E712
            )
            .update({"is_read": True, "read_at": now}, synchronize_session="fetch")
        )
        self._db.commit()
        return count

    def _get_or_404(self, notif_id: int) -> Notification:
        notif = self._db.get(Notification, notif_id)
        if notif is None:
            raise NotFoundError("Notification", str(notif_id))
        return notif
