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


class TimelinePoint(BaseModel):
    """时序数据点。"""

    date: str  # YYYY-MM-DD
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


class VulnerabilityTrend(BaseModel):
    """漏洞趋势。"""

    date: str
    new_pocs: int
    new_vulns: int


class TagDistItem(BaseModel):
    """标签命名空间分布项。"""

    tag_name: str
    count: int


class AssetSearchItem(BaseModel):
    """资产搜集命令分布项。"""

    key: str  # 语法名称，如 fofa / shodan（自动从 extra_meta 发现）
    count: int


class VulnTreemapItem(BaseModel):
    """CVE 影响范围矩形树图项。"""

    cve_id: str
    severity: str
    poc_count: int


class DashboardResponse(BaseModel):
    """Dashboard 完整响应。"""

    stats: DashboardStats
    severity_distribution: list[SeverityDistribution]
    status_distribution: list[StatusDistribution]
    creation_timeline: list[TimelinePoint]
    top_authors: list[TopAuthor]
    recent_activities: list[RecentActivityItem]
    asset_search_distribution: list[AssetSearchItem]
    vuln_coverage_treemap: list[VulnTreemapItem]