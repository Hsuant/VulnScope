"""Dashboard 统计服务：聚合 POC / CVE 数据生成可视化统计指标。"""

from __future__ import annotations

import datetime as dt
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.cache import cache
from app.core.config import settings
from app.core.timeutil import iso_utc
from app.models.poc import AuditLog, Poc, PocTag, Tag, Vuln

# ── 缓存键常量 ──────────────────────────────────────────────────────────

_CACHE_KEY_STATS = "dashboard:stats"
_CACHE_KEY_SEVERITY = "dashboard:severity"
_CACHE_KEY_STATUS = "dashboard:status"
_CACHE_KEY_TIMELINE = "dashboard:timeline"
_CACHE_KEY_AUTHORS = "dashboard:authors"
_CACHE_KEY_ACTIVITY = "dashboard:activity"
_CACHE_KEY_TREND = "dashboard:trend"
_CACHE_KEY_TAG_DIST = "dashboard:tag_dist"
_CACHE_KEY_ASSET_SEARCH = "dashboard:asset_search"
_CACHE_KEY_VULN_HEATMAP = "dashboard:vuln_heatmap"


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
            "timestamp": iso_utc(log.created_at) or "",
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


def get_tag_namespace_distribution(db: Session, namespace: str) -> list[dict]:
    """标签命名空间分布：获取指定命名空间下各标签的 POC 关联数。"""
    cache_key = f"{_CACHE_KEY_TAG_DIST}:{namespace}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    rows = db.execute(
        select(Tag.name, func.count().label("count"))
        .join(PocTag, Tag.id == PocTag.tag_id)
        .where(Tag.namespace == namespace)
        .group_by(Tag.id)
        .order_by(func.count().desc())
    ).all()
    result = [{"tag_name": r[0], "count": r[1]} for r in rows]
    cache.set(cache_key, result, ttl=settings.DASHBOARD_CACHE_TTL)
    return result


def get_asset_search_distribution(db: Session) -> list[dict]:
    """资产搜集命令分布：统计每种资产搜集语法的 POC 覆盖数（非互斥，可扩展）。"""
    cached = cache.get(_CACHE_KEY_ASSET_SEARCH)
    if cached:
        return cached

    rows = db.execute(select(Poc.extra_meta)).all()
    counts: dict[str, int] = {}
    for (meta,) in rows:
        meta_dict = meta or {}
        for key, val in meta_dict.items():
            if key.endswith("_syntax") and val:
                name = key.replace("_syntax", "")
                counts[name] = counts.get(name, 0) + 1

    result = [{"key": k, "count": v} for k, v in sorted(counts.items(), key=lambda x: -x[1])]
    cache.set(_CACHE_KEY_ASSET_SEARCH, result, ttl=settings.DASHBOARD_CACHE_TTL)
    return result


# ── CVE 厂商×CVSS 评分 热力图 ──────────────────────────────────────────

# CVSS 评分分桶标签：索引 0 为"未评分"（cvss 为空），索引 1..11 对应
# 评分 0..10。每个数值分桶覆盖 [n, n+1) 区间；10 分桶仅收纳恰好为 10.0 的项。
_CVSS_BUCKET_LABELS: list[str] = ["未评分"] + [str(i) for i in range(11)]
# "未评分"桶在 y_labels 中的索引位置。
_BUCKET_INDEX_UNRATED = 0
# CVSS 评分的有效上下界，用于 clamp，防止脏数据越界。
_CVSS_MIN, _CVSS_MAX = 0.0, 10.0


class VulnHeatmapAggregator:
    """将 CVE（厂商 + CVSS 评分）聚合为二维热力矩阵。

    该类为无状态数据加工对象：构造时接收原始行集与 Top-N 厂商清单，
    build() 输出前端可直接消费的 ECharts 热力图数据结构。

    设计要点：
        - 横轴（x）：按关联 CVE 数取 Top-N 的厂商，NULL 厂商归入"未知"参与排序。
        - 纵轴（y）：CVSS 评分分桶（0..10 + 未评分），高分置于顶部。
        - 单元格数值：落入该厂商×评分格子的 CVE 数量。

    采用面向对象封装聚合逻辑，使服务层保持轻量、便于单测复用。
    """

    def __init__(self, rows: list[tuple], top_vendors: list[str]) -> None:
        """初始化聚合器。

        Args:
            rows: 数据库查询结果，每行为 (厂商名, cvss 评分)。
            top_vendors: 已按 CVE 数降序排定的 Top-N 厂商清单（横轴顺序）。
        """
        self._rows = rows
        self._top_vendors = top_vendors
        # 厂商名 → 横轴索引，O(1) 定位，避免遍历查找。
        self._vendor_index: dict[str, int] = {v: i for i, v in enumerate(top_vendors)}

    def build(self) -> dict:
        """构建热力图数据结构。

        Returns:
            包含 x_labels / y_labels / cells 三字段字典：
            - x_labels: 厂商名列表（横轴）。
            - y_labels: CVSS 分桶标签列表（纵轴，高分在顶）。
            - cells: [x_index, y_index, count] 三元组列表（全量矩阵，含 0）。
        """
        matrix = self._init_matrix()
        for vendor, cvss in self._rows:
            xi = self._vendor_index.get(vendor)
            if xi is None:
                # 防御性兜底：仅统计 Top-N 厂商，跳过越界数据。
                continue
            yi = self._bucket_index(cvss)
            matrix[xi][yi] += 1

        # 展平为 ECharts 所需 [x, y, value] 三元组（全量，含 0），
        # 保证前端热力网格完整渲染，空格子以最小色阶呈现。
        cells = [
            [xi, yi, matrix[xi][yi]]
            for xi in range(len(self._top_vendors))
            for yi in range(len(_CVSS_BUCKET_LABELS))
        ]
        return {
            "x_labels": list(self._top_vendors),
            "y_labels": list(_CVSS_BUCKET_LABELS),
            "cells": cells,
        }

    def _init_matrix(self) -> list[list[int]]:
        """初始化 厂商×分桶 的二维零矩阵。"""
        return [[0] * len(_CVSS_BUCKET_LABELS) for _ in self._top_vendors]

    @staticmethod
    def _bucket_index(cvss: float | None) -> int:
        """将 CVSS 评分映射到纵轴分桶索引。

        Args:
            cvss: CVSS 评分（0.0~10.0），None 表示未评分。

        Returns:
            分桶索引：0=未评分，1..11 对应 0..10 分桶。
        """
        if cvss is None:
            return _BUCKET_INDEX_UNRATED
        # 防御性 clamp，避免脏数据（负值/越界）导致索引异常。
        score = max(_CVSS_MIN, min(_CVSS_MAX, float(cvss)))
        # int() 向零截断，等价于 floor（CVSS 恒 >= 0）。
        return int(score) + 1


def get_vuln_vendor_cvss_heatmap(db: Session, vendor_limit: int = 15) -> dict:
    """CVE 厂商×CVSS 评分热力图：横轴厂商、纵轴评分、数值为该格 CVE 数。

    Args:
        db: 数据库会话。
        vendor_limit: 横轴保留的厂商数量上限（按关联 CVE 数降序）。

    Returns:
        见 VulnHeatmapAggregator.build() 返回结构。
    """
    cache_key = f"{_CACHE_KEY_VULN_HEATMAP}:{vendor_limit}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    # 使用 coalesce 将 NULL 厂商归入"未知"，使其能参与 IN 过滤与排序。
    vendor_expr = func.coalesce(Vuln.vendor, "未知")

    # 1) 取关联 CVE 数 Top-N 的厂商（NULL 已归入"未知"参与排序）。
    top_rows = db.execute(
        select(vendor_expr, func.count().label("count"))
        .group_by(vendor_expr)
        .order_by(func.count().desc())
        .limit(vendor_limit)
    ).all()
    top_vendors = [r[0] for r in top_rows]

    # 2) 仅取 Top 厂商的 (厂商, cvss) 行，交由聚合器分桶，控制数据量。
    rows: list[tuple] = []
    if top_vendors:
        rows = db.execute(
            select(vendor_expr, Vuln.cvss).where(vendor_expr.in_(top_vendors))
        ).all()

    result = VulnHeatmapAggregator(rows, top_vendors).build()
    cache.set(cache_key, result, ttl=settings.DASHBOARD_CACHE_TTL)
    return result


def get_full_dashboard(db: Session) -> dict:
    """获取 Dashboard 完整数据（一次调用聚合所有统计，减并发）。"""
    return {
        "stats": get_stats(db),
        "severity_distribution": get_severity_distribution(db),
        "status_distribution": get_status_distribution(db),
        "vulnerability_trend": get_vulnerability_trend(db),
        "top_authors": get_top_authors(db),
        "recent_activities": get_recent_activities(db),
        "asset_search_distribution": get_asset_search_distribution(db),
        "vuln_vendor_cvss_heatmap": get_vuln_vendor_cvss_heatmap(db),
    }


def invalidate_cache() -> None:
    """Dashboard 数据变更时清除所有缓存（由事件总线消费者调用）。"""
    for key in [
        _CACHE_KEY_STATS,
        _CACHE_KEY_SEVERITY,
        _CACHE_KEY_STATUS,
        _CACHE_KEY_TIMELINE,
        _CACHE_KEY_AUTHORS,
        _CACHE_KEY_ACTIVITY,
        _CACHE_KEY_TREND,
        _CACHE_KEY_TAG_DIST,
        _CACHE_KEY_ASSET_SEARCH,
        _CACHE_KEY_VULN_HEATMAP,
    ]:
        cache.delete(key)
