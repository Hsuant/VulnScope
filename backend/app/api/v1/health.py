"""健康检查：浅探（DB）+ 深探（DB 完整度 / 缓存 / 插件 / 启动）。

- ``GET /health``        存活 + DB 连通性（兼容原探针签名，编排 healthcheck 使用）。
- ``GET /health/detail`` 逐组件探活并返回结构化结果；任一失败 HTTP 503，
  但每个检查独立 catch，失败项照实列出，不掩盖其余成功项。
"""

from __future__ import annotations

from typing import Any, cast

from fastapi import APIRouter, Depends, Request
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from starlette.responses import JSONResponse

from app.core.cache import get_cache
from app.core.logging import get_logger
from app.db.init_db import _verify_schema
from app.db.session import get_db
from app.plugins.registry import registry
from app.schemas.common import ok

logger = get_logger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health")
def health(request: Request, db: Session = Depends(get_db)) -> dict:
    """存活 + 数据库连通性探测。"""
    db.execute(text("SELECT 1"))
    return ok({"status": "ok", "db": "up"}, request)


# ── 深探：逐组件自检 ──────────────────────────────────────────────────────


def _probe_db_detail(db: Session) -> dict:
    """DB 连通 + schema 完整性（复用 init_db 的清单校验）。"""
    try:
        db.execute(text("SELECT 1"))
        _verify_schema(cast("Engine", db.get_bind()))
        return {"component": "db", "status": "up", "error": None}
    except Exception as exc:  # noqa: BLE001 - 单个探针失败不能中断整组检查
        logger.warning("health probe failed", extra={"component": "db", "error": str(exc)})
        return {"component": "db", "status": "down", "error": str(exc)}


def _probe_cache() -> dict:
    """缓存自检：写入→读取→删除闭环，验证 get/set/delete 全链路。"""
    from app.core.config import settings

    probe = get_cache()
    key = "health:probe"
    value = "pong"
    probe.set(key, value, ttl=5)
    readback = probe.get(key)
    probe.delete(key)
    up = readback == value
    return {
        "component": "cache",
        "status": "up" if up else "down",
        "backend": settings.CACHE_BACKEND,
        "msg": f"cache backend={settings.CACHE_BACKEND}, probe {'ok' if up else 'failed'}",
        "error": None if up else f"回读失败: {readback!r}",
    }


def _probe_plugins() -> dict:
    """插件加载状态：列出每个插件的名称 + 版本 + 启用状态（启动期已 discover）。"""
    entries = registry.list()
    # 按槽位分组，每组内按名称排序，便于阅读。
    grouped: dict[str, list[dict[str, Any]]] = {}
    for entry in sorted(entries, key=lambda e: (e.slot, e.name)):
        grouped.setdefault(entry.slot, []).append(
            {
                "name": entry.name,
                "version": entry.version,
                "enabled": entry.enabled,
            }
        )
    total = len(entries)
    return {
        "component": "plugins",
        "status": "up" if entries else "degraded",  # 空注册表为 degrade 而非 down
        "total": total,
        "slots": {slot: len(items) for slot, items in grouped.items()},
        "plugins": grouped,
        "msg": f"{total} plugins loaded across {len(grouped)} slots",
        "error": None,
    }


def _probe_startup() -> dict:
    """启动生命周期标记：中间件在 lifespan 完成后写入。"""
    return {
        "component": "startup",
        "status": "up" if _startup_completed else "down",
        "error": None if _startup_completed else "应用启动未完成",
    }


_startup_completed = False


def mark_startup_completed() -> None:
    """由 lifespan 结束（yield 后）回调，标记启动期已完成。"""
    global _startup_completed
    _startup_completed = True


@router.get("/health/detail", response_model=None)
def health_detail(request: Request, db: Session = Depends(get_db)) -> dict | JSONResponse:
    """深探：DB（连通+完整性）/ 缓存 / 插件 / 启动 分组报告。"""
    probes: list[dict[str, Any]] = [
        _probe_db_detail(db),
        _probe_cache(),
        _probe_plugins(),
        _probe_startup(),
    ]

    # 同步写入 Prometheus 探活 Gauge（供 /metrics 反映组件状态）。
    from app.core.metrics import init_metrics

    handles = init_metrics()
    for p in probes:
        status = p["status"]
        if p["component"] == "db":
            handles["db_health"].set(1 if status == "up" else 0)
        elif p["component"] == "cache":
            handles["cache_health"].set(1 if status == "up" else 0)
        elif p["component"] == "plugins":
            handles["plugins_loaded"].set(p.get("total", 0))

    all_up = all(p["status"] == "up" for p in probes)
    payload = {"status": "ok" if all_up else "degraded", "components": probes}
    if not all_up:
        return JSONResponse(
            status_code=503,
            content={"code": "SERVICE_DEGRADED", "message": "部分组件异常", "data": payload},
        )
    return ok(payload, request)
