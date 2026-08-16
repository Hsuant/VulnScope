"""Dashboard 统计 API：为前端可视化看板提供聚合数据。"""

from __future__ import annotations

from fastapi import APIRouter, Query, Request

from app.api.deps import CurrentUser, DbSession
from app.schemas.common import ok
from app.services import dashboard_service

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats")
def get_stats(request: Request, db: DbSession, user: CurrentUser) -> dict:
    """总览统计卡片：POC 总数、活跃数、漏洞数、标签数、作者数。"""
    return ok(dashboard_service.get_stats(db), request)


@router.get("/severity")
def get_severity_distribution(request: Request, db: DbSession, user: CurrentUser) -> dict:
    """严重级别分布（饼图/柱状图）：info / low / medium / high / critical。"""
    return ok(dashboard_service.get_severity_distribution(db), request)


@router.get("/status")
def get_status_distribution(request: Request, db: DbSession, user: CurrentUser) -> dict:
    """状态分布（饼图）：draft / active / disabled / archived。"""
    return ok(dashboard_service.get_status_distribution(db), request)


@router.get("/timeline")
def get_creation_timeline(
    request: Request,
    db: DbSession,
    user: CurrentUser,
    days: int = Query(default=30, ge=7, le=365, description="统计天数"),
) -> dict:
    """POC 创建趋势（折线图）：按天聚合最近 N 天数据，缺失日期补 0。"""
    return ok(dashboard_service.get_creation_timeline(db, days), request)


@router.get("/top-authors")
def get_top_authors(
    request: Request,
    db: DbSession,
    user: CurrentUser,
    limit: int = Query(default=10, ge=1, le=50, description="返回条数"),
) -> dict:
    """高产作者排名（柱状图）：按 POC 发布数降序排列。"""
    return ok(dashboard_service.get_top_authors(db, limit), request)


@router.get("/recent-activities")
def get_recent_activities(
    request: Request,
    db: DbSession,
    user: CurrentUser,
    limit: int = Query(default=10, ge=1, le=50, description="返回条数"),
) -> dict:
    """最近活动列表（时间线）：POC 创建/更新/状态变更记录。"""
    return ok(dashboard_service.get_recent_activities(db, limit), request)


@router.get("/trend")
def get_vulnerability_trend(
    request: Request,
    db: DbSession,
    user: CurrentUser,
    days: int = Query(default=30, ge=7, le=365, description="统计天数"),
) -> dict:
    """漏洞趋势对比（双轴折线图）：POC 新增量 vs CVE 新增量。"""
    return ok(dashboard_service.get_vulnerability_trend(db, days), request)


@router.get("/tag-distribution")
def get_tag_namespace_distribution(
    request: Request,
    db: DbSession,
    user: CurrentUser,
    namespace: str = Query(..., description="标签命名空间"),
) -> dict:
    """标签命名空间分布（饼图）：选定命名空间下各子标签的 POC 关联数。"""
    return ok(dashboard_service.get_tag_namespace_distribution(db, namespace), request)


@router.get("/asset-search-distribution")
def get_asset_search_distribution(request: Request, db: DbSession, user: CurrentUser) -> dict:
    """资产搜集命令分布（饼图）：统计 POC 中 FOFA / Shodan 语法的覆盖情况。"""
    return ok(dashboard_service.get_asset_search_distribution(db), request)


@router.get("/vuln-treemap")
def get_vuln_coverage_treemap(
    request: Request,
    db: DbSession,
    user: CurrentUser,
    limit: int = Query(default=20, ge=5, le=50, description="返回条数"),
) -> dict:
    """CVE 影响范围矩形树图：展示 CVE 编号及其关联 POC 数。"""
    return ok(dashboard_service.get_vuln_coverage_treemap(db, limit), request)


@router.get("/full")
def get_full_dashboard(request: Request, db: DbSession, user: CurrentUser) -> dict:
    """Dashboard 全量数据（一次聚合所有统计，减少前端并发请求）。"""
    return ok(dashboard_service.get_full_dashboard(db), request)
