"""Dashboard 统计服务：聚合 POC 数据生成可视化统计指标。"""

from __future__ import annotations

import datetime as dt
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.cache import cache
from app.core.config import settings
from app.models.poc import AuditLog, Poc, PocTag, Tag, Vuln

# ── 缓存键常量 ──────────────────────────────────────────────────────────

_CACHE_KEY_STATS = "dashboard:stats"
_CACHE_KEY_SEVERITY = "dashboard:severity"
_CACHE_KEY_STATUS = "dashboard:status"
_CACHE_KEY_SOURCE = "dashboard:source"
_CACHE_KEY_FORMAT = "dashboard:format"
_CACHE_KEY_TIMELINE = "dashboard:timeline"
_CACHE_KEY_TAGS = "dashboard:tags"
_CACHE_KEY_AUTHORS = "dashboard:authors"
_CACHE_KEY_ACTIVITY = "dashboard:activity"
_CACHE_KEY_TREND = "dashboard:trend"
_CACHE_KEY_TAG_CLOUD = "dashboard:tag_cloud"


# ── 统计聚合函数 ────────────────────────────────────────────────────────


def _safe_count(db: Session, column: Any) -> list[dict]:
    """通用 GROUP BY 计数，返回 [{key, count}] 列表。"""
    rows = db.execute(
        select(column, func.count().label("count")).group_by(column).order_by(func.count().desc())
    )
    return [{"key": row[0] or "unknown", "count": row[1]} for row in rows]


def get_stats(db: Session) -> dict:
    """总览统计：总数 / 活跃数 / 漏洞数 / 标签数 / 分类数 / 作者数。"""
    cached = cache.get(_CACHE_KEY_STATS)
    if cached:
        return cached

    total_pocs = db.scalar(select(func.count(Poc.id))) or 0
    total_active = db.scalar(select(func.count(Poc.id)).where(Poc.status == "active")) or 0
    total_vulns = db.scalar(select(func.count(Vuln.id))) or 0
    total_tags = db.scalar(select(func.count(Tag.id))) or 0
    # 分类数通过 DISTINCT category 查询
    # 作者数
    author_count = db.scalar(select(func.count(func.distinct(Poc.author))).where(Poc.author.isnot(None))) or 0

    result = {
        "total_pocs": total_pocs,
        "total_active_pocs": total_active,
        "total_vulns": total_vulns,
        "total_tags": total_tags,
        "total_categories": 0,  # 分类暂未实现完整统计，留占位
        "total_authors": author_count,
    }
    cache.set(_CACHE_KEY_STATS, result, ttl=settings.DASHBOARD_CACHE_TTL)
    return result


def get_severity_distribution(db: Session) -> list[dict]:
    """严重级别分布。"""
    cached = cache.get(_CACHE_KEY_SEVERITY)
    if cached:
        return cached
    result = _safe_count(db, Poc.severity)
    cache.set(_CACHE_KEY_SEVERITY, result, ttl=settings.DASHBOARD_CACHE_TTL)
    return result


def get_status_distribution(db: Session) -> list[dict]:
    """状态分布。"""
    cached = cache.get(_CACHE_KEY_STATUS)
    if cached:
        return cached
    result = _safe_count(db, Poc.status)
    cache.set(_CACHE_KEY_STATUS, result, ttl=settings.DASHBOARD_CACHE_TTL)
    return result


def get_source_distribution(db: Session) -> list[dict]:
    """来源分布。"""
    cached = cache.get(_CACHE_KEY_SOURCE)
    if cached:
        return cached
    result = _safe_count(db, Poc.source)
    cache.set(_CACHE_KEY_SOURCE, result, ttl=settings.DASHBOARD_CACHE_TTL)
    return result


def get_format_distribution(db: Session) -> list[dict]:
    """格式分布。"""
    cached = cache.get(_CACHE_KEY_FORMAT)
    if cached:
        return cached
    result = _safe_count(db, Poc.format)
    cache.set(_CACHE_KEY_FORMAT, result, ttl=settings.DASHBOARD_CACHE_TTL)
    return result


def get_creation_timeline(db: Session, days: int = 30) -> list[dict]:
    """POC 创建趋势（最近 N 天，按天聚合）。"""
    cache_key = f"{_CACHE_KEY_TIMELINE}:{days}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    since = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days)
    rows = db.execute(
        select(
            func.date(Poc.created_at).label("date"),
            func.count().label("count"),
        )
        .where(Poc.created_at >= since)
        .group_by(func.date(Poc.created_at))
        .order_by(func.date(Poc.created_at))
    ).all()

    # 填充缺失日期（保证前端折线图连续）
    date_counts: dict[str, int] = {str(r[0]): r[1] for r in rows}
    result = []
    for i in range(days):
        d = (since + dt.timedelta(days=i)).strftime("%Y-%m-%d")
        result.append({"date": d, "count": date_counts.get(d, 0)})

    cache.set(cache_key, result, ttl=settings.DASHBOARD_CACHE_TTL)
    return result


def get_top_tags(db: Session, limit: int = 10) -> list[dict]:
    """热门标签（按 POC 关联数排序）。"""
    cache_key = f"{_CACHE_KEY_TAGS}:{limit}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    rows = db.execute(
        select(Tag.name, Tag.namespace, func.count().label("count"))
        .join(PocTag, Tag.id == PocTag.tag_id)
        .group_by(Tag.id)
        .order_by(func.count().desc())
        .limit(limit)
    ).all()
    result = [{"tag_name": r[0], "namespace": r[1], "count": r[2]} for r in rows]
    cache.set(cache_key, result, ttl=settings.DASHBOARD_CACHE_TTL)
    return result


def get_top_authors(db: Session, limit: int = 10) -> list[dict]:
    """高产作者（按 POC 数量排序）。"""
    cache_key = f"{_CACHE_KEY_AUTHORS}:{limit}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    rows = db.execute(
        select(Poc.author, func.count().label("count"))
        .where(Poc.author.isnot(None))
        .group_by(Poc.author)
        .order_by(func.count().desc())
        .limit(limit)
    ).all()
    result = [{"author": r[0], "count": r[1]} for r in rows]
    cache.set(cache_key, result, ttl=settings.DASHBOARD_CACHE_TTL)
    return result


def get_recent_activities(db: Session, limit: int = 10) -> list[dict]:
    """最近活动（审计日志）。"""
    cached = cache.get(_CACHE_KEY_ACTIVITY)
    if cached:
        return cached

    rows = db.execute(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)).scalars().all()
    result = [
        {
            "poc_id": (
                log.resource_id and int(log.resource_id)
                if log.resource_id and log.resource_id.isdigit()
                else 0
            ),
            "poc_name": (log.detail or {}).get("poc_name", ""),
            "action": log.action,
            "timestamp": log.created_at.isoformat() if log.created_at else "",
        }
        for log in rows
    ]
    cache.set(_CACHE_KEY_ACTIVITY, result, ttl=settings.DASHBOARD_CACHE_TTL)
    return result


def get_vulnerability_trend(db: Session, days: int = 30) -> list[dict]:
    """漏洞趋势（POC 新增 vs 漏洞新增，按天）。"""
    cache_key = f"{_CACHE_KEY_TREND}:{days}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    since = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days)

    poc_rows = db.execute(
        select(
            func.date(Poc.created_at).label("date"),
            func.count().label("count"),
        )
        .where(Poc.created_at >= since)
        .group_by(func.date(Poc.created_at))
        .order_by(func.date(Poc.created_at))
    ).all()

    vuln_rows = []
    if hasattr(Vuln, "created_at"):
        vuln_rows = list(
            db.execute(
                select(
                    func.date(Vuln.created_at).label("date"),
                    func.count().label("count"),
                )
                .where(Vuln.created_at >= since)
                .group_by(func.date(Vuln.created_at))
                .order_by(func.date(Vuln.created_at))
            ).all()
        )

    poc_map: dict[str, int] = {str(r[0]): r[1] for r in poc_rows}
    vuln_map: dict[str, int] = {str(r[0]): r[1] for r in vuln_rows}

    result = []
    for i in range(days):
        d = (since + dt.timedelta(days=i)).strftime("%Y-%m-%d")
        result.append({"date": d, "new_pocs": poc_map.get(d, 0), "new_vulns": vuln_map.get(d, 0)})

    cache.set(cache_key, result, ttl=settings.DASHBOARD_CACHE_TTL)
    return result


def get_tag_cloud(db: Session) -> list[dict]:
    """标签云（按命名空间分组）。"""
    cached = cache.get(_CACHE_KEY_TAG_CLOUD)
    if cached:
        return cached

    rows = db.execute(
        select(Tag.namespace, Tag.name, func.count().label("count"))
        .join(PocTag, Tag.id == PocTag.tag_id)
        .group_by(Tag.id)
        .order_by(Tag.namespace, func.count().desc())
    ).all()

    ns_map: dict[str, list[dict]] = {}
    for r in rows:
        ns_map.setdefault(r[0], []).append({"tag_name": r[1], "namespace": r[0], "count": r[2]})

    result = [{"namespace": ns, "tags": tags} for ns, tags in ns_map.items()]
    cache.set(_CACHE_KEY_TAG_CLOUD, result, ttl=settings.DASHBOARD_CACHE_TTL)
    return result


def get_full_dashboard(db: Session) -> dict:
    """获取 Dashboard 完整数据（一次调用聚合所有统计，减并发）。"""
    return {
        "stats": get_stats(db),
        "severity_distribution": get_severity_distribution(db),
        "status_distribution": get_status_distribution(db),
        "source_distribution": get_source_distribution(db),
        "format_distribution": get_format_distribution(db),
        "creation_timeline": get_creation_timeline(db),
        "top_tags": get_top_tags(db),
        "top_authors": get_top_authors(db),
        "recent_activities": get_recent_activities(db),
    }


def invalidate_cache() -> None:
    """Dashboard 数据变更时清除所有缓存（由事件总线消费者调用）。"""
    for key in [
        _CACHE_KEY_STATS,
        _CACHE_KEY_SEVERITY,
        _CACHE_KEY_STATUS,
        _CACHE_KEY_SOURCE,
        _CACHE_KEY_FORMAT,
        _CACHE_KEY_TIMELINE,
        _CACHE_KEY_TAGS,
        _CACHE_KEY_AUTHORS,
        _CACHE_KEY_ACTIVITY,
        _CACHE_KEY_TREND,
        _CACHE_KEY_TAG_CLOUD,
    ]:
        cache.delete(key)
