"""POC 相关 Pydantic schema：请求校验、响应序列化、查询参数。"""

from __future__ import annotations

import datetime as dt
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

# ── 合法值枚举（与存储层应用层校验一致） ──────────────────────────────────

POC_SEVERITIES = {"info", "low", "medium", "high", "critical"}
POC_STATUSES = {"draft", "active", "disabled", "archived"}
POC_SOURCES = {"manual", "imported", "ai", "crawler"}
POC_FORMATS = {"nuclei-yaml", "json", "pocsuite3", "raw-script"}

# 状态流转规则：key -> 允许的目标状态集合
STATUS_TRANSITIONS: dict[str, set[str]] = {
    "draft": {"active", "disabled"},
    "active": {"disabled", "archived"},
    "disabled": {"active", "archived"},
    "archived": {"active"},
}

# 严重级别排序权重（用于按严重程度排序）
SEVERITY_ORDER = {"info": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}


# ── 标签/漏洞/分类的简要结构（避免循环引用） ──────────────────────────────


class TagBrief(BaseModel):
    """标签简要信息，嵌入 POC 响应中使用。"""

    id: int
    namespace: str
    name: str
    color: str | None = None


class CategoryBrief(BaseModel):
    """分类简要信息。"""

    id: int
    name: str
    slug: str


class VulnBrief(BaseModel):
    """漏洞简要信息。"""

    id: int
    cve_id: str
    severity: str | None = None


# ── 版本影响范围 ──────────────────────────────────────────────────────────


class ReferenceItem(BaseModel):
    """参考链接条目。"""

    url: str = Field(..., max_length=512, description="参考链接 URL")
    label: str | None = Field(default=None, max_length=128, description="链接标签/标题")


class AffectedVersion(BaseModel):
    """版本影响范围条目。"""

    version_start: str | None = Field(default=None, max_length=32, description="起始版本")
    version_start_type: str = Field(default=">=", max_length=8, description="起始操作符: >=, >, 留空表示任意")
    version_end: str | None = Field(default=None, max_length=32, description="截止版本")
    version_end_type: str = Field(default="<=", max_length=8, description="截止操作符: <=, <, 留空表示任意")


# ── 请求体 ──────────────────────────────────────────────────────────────


class PocCreate(BaseModel):
    """创建 POC 请求体。"""

    name: str = Field(
        min_length=1,
        max_length=128,
        pattern=r"^[a-zA-Z0-9一-龥][a-zA-Z0-9一-龥. \-]*$",
        description="POC 业务名，如 struts2-s2-045-rce",
    )
    title: str | None = Field(default=None, max_length=255, description="中文/显示标题")
    description: str | None = Field(default=None, description="漏洞描述")
    severity: str = Field(default="info", description="严重级别")
    format: str = Field(default="nuclei-yaml", description="POC 格式")
    language: str | None = Field(default=None, max_length=32, description="脚本语言")
    content: str = Field(..., min_length=1, description="POC 内容主体")
    author: str | None = Field(default=None, max_length=128, description="作者")
    source: str = Field(default="manual", description="来源类型")
    status: str = Field(default="draft", description="状态")
    cve_ids: list[str] = Field(default_factory=list, description="关联 CVE 编号列表")
    cnvd_ids: list[str] = Field(default_factory=list, description="关联 CNVD/CNNVD 编号列表")
    references: list[ReferenceItem] = Field(default_factory=list, description="参考链接列表")
    fofa_syntax: str | None = Field(default=None, max_length=1024, description="资产探测 FOFA 语法")
    shodan_syntax: str | None = Field(default=None, max_length=1024, description="资产探测 Shodan 语法")
    tag_ids: list[int] = Field(default_factory=list, description="关联标签 ID 列表")
    category_ids: list[int] = Field(default_factory=list, description="关联分类 ID 列表")
    affected_versions: list[AffectedVersion] = Field(default_factory=list, description="版本影响范围列表")
    extra_meta: dict[str, Any] = Field(default_factory=dict, description="扩展元数据")

    @field_validator("severity")
    @classmethod
    def _check_severity(cls, v: str) -> str:
        if v not in POC_SEVERITIES:
            raise ValueError(f"非法 severity: {v}，可选: {', '.join(sorted(POC_SEVERITIES))}")
        return v

    @field_validator("status")
    @classmethod
    def _check_status(cls, v: str) -> str:
        if v not in POC_STATUSES:
            raise ValueError(f"非法 status: {v}，可选: {', '.join(sorted(POC_STATUSES))}")
        return v

    @field_validator("source")
    @classmethod
    def _check_source(cls, v: str) -> str:
        if v not in POC_SOURCES:
            raise ValueError(f"非法 source: {v}，可选: {', '.join(sorted(POC_SOURCES))}")
        return v

    @field_validator("format")
    @classmethod
    def _check_format(cls, v: str) -> str:
        if v not in POC_FORMATS:
            raise ValueError(f"非法 format: {v}，可选: {', '.join(sorted(POC_FORMATS))}")
        return v


class PocUpdate(BaseModel):
    """更新 POC 请求体（所有字段可选）。"""

    name: str | None = Field(
        default=None, min_length=1, max_length=128, pattern=r"^[a-zA-Z0-9一-龥][a-zA-Z0-9一-龥. \-]*$"
    )
    title: str | None = Field(default=None, max_length=255)
    description: str | None = None
    severity: str | None = None
    format: str | None = None
    language: str | None = None
    content: str | None = None
    author: str | None = None
    source: str | None = None
    status: str | None = None
    cve_ids: list[str] | None = None
    cnvd_ids: list[str] | None = None
    references: list[ReferenceItem] | None = None
    fofa_syntax: str | None = Field(default=None, max_length=1024, description="资产探测 FOFA 语法")
    shodan_syntax: str | None = Field(default=None, max_length=1024, description="资产探测 Shodan 语法")
    tag_ids: list[int] | None = None
    category_ids: list[int] | None = None
    affected_versions: list[AffectedVersion] | None = None
    extra_meta: dict[str, Any] | None = None

    @field_validator("severity")
    @classmethod
    def _check_severity(cls, v: str | None) -> str | None:
        if v is not None and v not in POC_SEVERITIES:
            raise ValueError(f"非法 severity: {v}")
        return v

    @field_validator("status")
    @classmethod
    def _check_status(cls, v: str | None) -> str | None:
        if v is not None and v not in POC_STATUSES:
            raise ValueError(f"非法 status: {v}")
        return v

    @field_validator("source")
    @classmethod
    def _check_source(cls, v: str | None) -> str | None:
        if v is not None and v not in POC_SOURCES:
            raise ValueError(f"非法 source: {v}")
        return v

    @field_validator("format")
    @classmethod
    def _check_format(cls, v: str | None) -> str | None:
        if v is not None and v not in POC_FORMATS:
            raise ValueError(f"非法 format: {v}")
        return v


class PocStatusChange(BaseModel):
    """状态变更请求体。"""

    status: str = Field(..., description="目标状态")

    @field_validator("status")
    @classmethod
    def _check_status(cls, v: str) -> str:
        if v not in POC_STATUSES:
            raise ValueError(f"非法 status: {v}")
        return v


class PocCloneRequest(BaseModel):
    """克隆 POC 请求体。"""

    name: str = Field(
        ...,
        min_length=1,
        max_length=128,
        pattern=r"^[a-zA-Z0-9一-龥][a-zA-Z0-9一-龥. \-]*$",
        description="新 POC 的业务名",
    )


# ── 响应体 ──────────────────────────────────────────────────────────────


class PocListItem(BaseModel):
    """POC 列表项（不含 content 全文，节省带宽）。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    uuid: str
    name: str
    title: str | None = None
    severity: str = "info"
    format: str = "nuclei-yaml"
    source: str = "manual"
    status: str = "draft"
    author: str | None = None
    version: int = 1
    tags: list[TagBrief] = []
    cve_ids: list[str] = []
    created_at: dt.datetime | None = None
    updated_at: dt.datetime | None = None


class PocResponse(BaseModel):
    """POC 完整详情（含 content 全文和所有关联数据）。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    uuid: str
    name: str
    title: str | None = None
    description: str | None = None
    severity: str = "info"
    format: str = "nuclei-yaml"
    language: str | None = None
    content: str
    content_hash: str
    author: str | None = None
    source: str = "manual"
    status: str = "draft"
    version: int = 1
    extra_meta: dict[str, Any] | None = None
    tags: list[TagBrief] = []
    cve_ids: list[str] = []
    cnvd_ids: list[str] = []
    references: list[ReferenceItem] = []
    fofa_syntax: str | None = None
    shodan_syntax: str | None = None
    categories: list[CategoryBrief] = []
    affected_versions: list[AffectedVersion] = []
    created_by: int | None = None
    updated_by: int | None = None
    created_at: dt.datetime | None = None
    updated_at: dt.datetime | None = None


class PocVersionResponse(BaseModel):
    """POC 版本历史条目。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    version_seq: int
    content_hash: str
    changed_by: int | None = None
    changed_at: dt.datetime | None = None


class PocImportResult(BaseModel):
    """导入结果报告。"""

    total: int = 0
    success: int = 0
    skipped: int = 0
    failed: list[dict] = []


# ── 查询参数 ────────────────────────────────────────────────────────────

# PocQueryParams 已移至 app/api/v1/poc.py，使用 fastapi.Query 声明查询参数。
