"""应用入口：FastAPI 实例装配。"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1 import health  # noqa: F401  (注册 /api/v1 路由)
from app.core.config import settings
from app.core.events import EventTypes, event_bus
from app.core.exceptions import register_exception_handlers
from app.db import init_db
from app.db.session import SessionLocal
from app.services import auth_service


def _dashboard_cache_invalidator(event) -> None:
    """Dashboard 缓存失效消费者：POC 变更时清除统计缓存。"""
    from app.services.dashboard_service import invalidate_cache

    invalidate_cache()


APP_NAME = settings.APP_NAME


@asynccontextmanager
async def lifespan(app: FastAPI):
    """启动期：初始化数据库结构（建表）+ 内置角色/管理员 + 事件消费者注册。

    init_db 仅建结构；角色与默认管理员作为应用级引导数据在此写入（幂等）。
    """
    try:
        init_db.init_db()
    except Exception as exc:  # 数据库未就绪时不允许静默，但调试期兜底
        if settings.APP_ENV != "dev":
            raise
        print(f"[bootstrap] skip init_db: {exc}")

    db = SessionLocal()
    try:
        auth_service.seed_roles(db)
        auth_service.seed_admin(db)
    finally:
        db.close()

    # 注册 Dashboard 缓存失效消费者（POC 变更时自动刷新统计）
    for event_type in EventTypes:
        event_bus.subscribe(event_type.value, _dashboard_cache_invalidator)
    print(f"[bootstrap] 已注册 Dashboard 缓存失效消费者，监听 {len(EventTypes)} 种事件")

    # 发现并加载内置插件
    from app.plugins.registry import registry

    registry.discover_internal()

    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title=APP_NAME,
        version="0.2.0",
        description="VulnScope POC 管理系统 API",
        lifespan=lifespan,
    )
    register_exception_handlers(app)

    # 挂载 v1 路由
    from app.api.v1 import audit, auth, dashboard, import_export, poc, tags, users, vulns
    from app.api.v1 import plugins as plugins_router

    api_prefix = settings.API_PREFIX
    app.include_router(health.router, prefix=api_prefix)
    app.include_router(auth.router, prefix=api_prefix)
    app.include_router(dashboard.router, prefix=api_prefix)
    app.include_router(poc.router, prefix=api_prefix)
    app.include_router(tags.router, prefix=api_prefix)
    app.include_router(vulns.router, prefix=api_prefix)
    app.include_router(audit.router, prefix=api_prefix)
    app.include_router(users.router, prefix=api_prefix)
    app.include_router(plugins_router.router, prefix=api_prefix)
    app.include_router(import_export.router, prefix=api_prefix)

    return app


app = create_app()
