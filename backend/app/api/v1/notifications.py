"""Notification API routes."""

from __future__ import annotations

from fastapi import APIRouter, Query, Request

from app.api.deps import CurrentUser, DbSession
from app.schemas.common import ok
from app.schemas.notification import NotificationListResponse, NotificationResponse
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("")
def list_notifications(
    request: Request,
    db: DbSession,
    user: CurrentUser,
    page: int = Query(default=1, ge=1, description="page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="items per page"),
    unread_only: bool = Query(default=False, description="unread only"),
) -> dict:
    service = NotificationService(db, user.id)
    items, total, unread_count = service.list_mine(page=page, page_size=page_size, unread_only=unread_only)
    sub_items = [NotificationResponse.model_validate(n).model_dump() for n in items]
    result = NotificationListResponse(
        items=sub_items, total=total, unread_count=unread_count, page=page, page_size=page_size
    )
    return ok(result.model_dump(), request)


@router.get("/unread-count")
def get_unread_count(
    request: Request,
    db: DbSession,
    user: CurrentUser,
) -> dict:
    service = NotificationService(db, user.id)
    count = service.unread_count()
    return ok({"unread_count": count}, request)


@router.put("/{notif_id}/read")
def mark_notification_read(
    request: Request,
    db: DbSession,
    user: CurrentUser,
    notif_id: int,
) -> dict:
    service = NotificationService(db, user.id)
    notif = service.mark_read(notif_id)
    return ok(NotificationResponse.model_validate(notif).model_dump(), request)


@router.put("/read-all")
def mark_all_read(
    request: Request,
    db: DbSession,
    user: CurrentUser,
) -> dict:
    service = NotificationService(db, user.id)
    count = service.mark_all_read()
    return ok({"marked_read": count}, request)
