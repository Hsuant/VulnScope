"""订阅 API 路由。"""

from __future__ import annotations

from fastapi import APIRouter, Query, Request

from app.api.deps import CurrentUser, DbSession
from app.schemas.common import Page, ok
from app.schemas.subscription import (
    SubscriptionCreate,
    SubscriptionResponse,
    SubscriptionUpdate,
)
from app.services.subscription_service import SubscriptionService

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


@router.post("")
def create_subscription(
    request: Request,
    db: DbSession,
    user: CurrentUser,
    body: SubscriptionCreate,
) -> dict:
    """创建订阅规则。"""
    service = SubscriptionService(db, user.id)
    sub = service.create(body)
    resp = SubscriptionResponse.model_validate(sub)
    resp.target_display = service.get_target_display(sub)
    return ok(resp.model_dump(), request)


@router.get("")
def list_subscriptions(
    request: Request,
    db: DbSession,
    user: CurrentUser,
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页条数"),
) -> dict:
    """分页查询当前用户的订阅列表。"""
    service = SubscriptionService(db, user.id)
    items, total = service.list_mine(page=page, page_size=page_size)
    sub_items = []
    for sub in items:
        resp = SubscriptionResponse.model_validate(sub)
        resp.target_display = service.get_target_display(sub)
        sub_items.append(resp.model_dump())
    result = Page.create(sub_items, total, page, page_size)
    return ok(result.model_dump(), request)


@router.put("/{sub_id}")
def update_subscription(
    request: Request,
    db: DbSession,
    user: CurrentUser,
    sub_id: int,
    body: SubscriptionUpdate,
) -> dict:
    """更新订阅通知偏好。"""
    service = SubscriptionService(db, user.id)
    sub = service.update(sub_id, body)
    return ok(SubscriptionResponse.model_validate(sub).model_dump(), request)


@router.delete("/{sub_id}")
def delete_subscription(
    request: Request,
    db: DbSession,
    user: CurrentUser,
    sub_id: int,
) -> dict:
    """取消订阅。"""
    service = SubscriptionService(db, user.id)
    service.delete(sub_id)
    return ok({"deleted": True, "subscription_id": sub_id}, request)