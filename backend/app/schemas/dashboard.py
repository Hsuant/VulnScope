"""Dashboard 统计相关 Pydantic schema。"""

from __future__ import annotations

from pydantic import BaseModel


class DashboardStats(BaseModel):
    """Dashboard 总览统计数据。"""

    total_pocs: int = 0
    total_active_pocs: int = 0
    total_vulns: int = 0
    total_tags: int = 0
    total_categories: int = 0
    total_authors: int = 0


class SeverityDistribution(BaseModel):
    """严重级别分布。"""

    severity: str
    count: int


class StatusDistribution(BaseModel):
    """状态分布。"""

    status: str
    count: int


class SourceDistribution(BaseModel):
    """来源分布。"""

    source: str
    count: int


class FormatDistribution(BaseModel):
    """格式分布。"""

    format: str
    count: int


class TimelinePoint(BaseModel):
    """时序数据点。"""

    date: str  # YYYY-MM-DD
    count: int


class TopTag(BaseModel):
    """热门标签。"""

    tag_name: str
    namespace: str
    count: int


class TopAuthor(BaseModel):
    """高产作者。"""

    author: str
    count: int


class RecentActivityItem(BaseModel):
    """最近活动条目。"""

    poc_id: int
    poc_name: str
    action: str  # created / updated / status_changed
    timestamp: str


class DashboardResponse(BaseModel):
    """Dashboard 完整响应。"""

    stats: DashboardStats
    severity_distribution: list[SeverityDistribution]
    status_distribution: list[StatusDistribution]
    source_distribution: list[SourceDistribution]
    format_distribution: list[FormatDistribution]
    creation_timeline: list[TimelinePoint]
    top_tags: list[TopTag]
    top_authors: list[TopAuthor]
    recent_activities: list[RecentActivityItem]


class VulnerabilityTrend(BaseModel):
    """漏洞趋势。"""

    date: str
    new_pocs: int
    new_vulns: int


class TagCloud(BaseModel):
    """标签云。"""

    namespaces: list[TagNamespace]


class TagNamespace(BaseModel):
    """标签命名空间。"""

    namespace: str
    tags: list[TopTag]
