"""插件管理 API 路由。

展示已发现/已注册的插件列表及状态。
"""

from __future__ import annotations

from fastapi import APIRouter, Request

from app.api.deps import CurrentUser, DbSession
from app.plugins.registry import registry
from app.schemas.common import ok

router = APIRouter(prefix="/plugins", tags=["plugins"])


@router.get("")
def list_plugins(request: Request, db: DbSession, user: CurrentUser) -> dict:
    """获取所有已注册插件列表（含槽位、名称、版本、启用状态）。"""
    entries = registry.list()
    items = [
        {
            "slot": e.slot,
            "name": e.name,
            "version": e.version,
            "enabled": e.enabled,
        }
        for e in entries
    ]
    return ok(items, request)


@router.get("/{slot}")
def list_plugins_by_slot(request: Request, db: DbSession, user: CurrentUser, slot: str) -> dict:
    """按槽位获取插件列表。"""
    entries = registry.list(slot=slot)
    if not entries:
        return ok([], request)
    items = [
        {
            "slot": e.slot,
            "name": e.name,
            "version": e.version,
            "enabled": e.enabled,
        }
        for e in entries
    ]
    return ok(items, request)
