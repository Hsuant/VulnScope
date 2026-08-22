"""应用入口：FastAPI 实例装配。"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1 import health  # noqa: F401  (注册 /api/v1 路由)
from app.core.config import settings
from app.core.events import EventTypes, event_bus
from app.core.exceptions import register_exception_handlers
from app.core.logging import get_logger, setup_logging
from app.db import init_db
from app.db.session import SessionLocal
from app.services import auth_service

logger = get_logger(__name__)


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
    # 安全闸门：生产环境校验 SECRET_KEY，未配置随机密钥则拒绝启动。
    settings.validate_security()

    try:
        init_db.init_db()
    except Exception as exc:  # 数据库未就绪时不允许静默，但调试期兜底
        if settings.APP_ENV != "dev":
            raise
        logger.warning("skip init_db: %s", exc)

    db = SessionLocal()
    try:
        auth_service.seed_roles(db)
        auth_service.seed_admin(db)
    finally:
        db.close()

    # 注册 Dashboard 缓存失效消费者（POC 变更时自动刷新统计）
    for event_type in EventTypes:
        event_bus.subscribe(event_type.value, _dashboard_cache_invalidator)
    logger.info("registered dashboard cache invalidator for %d event types", len(EventTypes))

    # 发现并加载内置插件
    from app.plugins.registry import registry

    registry.discover_internal()

    # 标记启动完成（健康检查深探使用）
    from app.api.v1.health import mark_startup_completed

    mark_startup_completed()

    yield


def create_app() -> FastAPI:
    setup_logging()

    app = FastAPI(
        title=APP_NAME,
        version="0.3.0",
        description="VulnScope POC 管理系统 API",
        lifespan=lifespan,
    )
    register_exception_handlers(app)

    # 中间件：请求度量（外）→ request_id 注入（内）→ 端点
    from app.core.metrics import RequestMetricsMiddleware
    from app.core.request_id import RequestIdContextMiddleware

    app.add_middleware(RequestMetricsMiddleware)
    app.add_middleware(RequestIdContextMiddleware)

    # 挂载 v1 路由
    from app.api.v1 import (
        audit,
        auth,
        dashboard,
        import_export,
        poc,
        products,
        tags,
        users,
        vulns,
    )
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
    app.include_router(products.router, prefix=api_prefix)

    # /metrics 挂载于根路径（Prometheus 传统约定，不套 API 前缀）
    from app.api.v1.metrics import router as metrics_router

    app.include_router(metrics_router)

    return app


app = create_app()
