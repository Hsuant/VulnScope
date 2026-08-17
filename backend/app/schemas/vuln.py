"""CVE 漏洞库相关 Pydantic schema。"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class VulnResponse(BaseModel):
    """CVE 漏洞响应体。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    cve_id: str
    title: str | None = None
    description: str | None = None
    cvss: float | None = None
    severity: str | None = None
    poc_count: int = 0
    created_at: str | None = None


class VulnList(BaseModel):
    """CVE 列表（含分页）。"""

    items: list[VulnResponse]
    total: int


class VulnCreate(BaseModel):
    """创建 CVE 请求体。"""

    cve_id: str = Field(..., pattern=r"^CVE-\d{4}-\d{4,}$", description="CVE 编号")
    title: str | None = Field(default=None, max_length=255)
    description: str | None = None
    cvss: float | None = Field(default=None, ge=0, le=10)
    severity: str | None = Field(default=None, max_length=16)


class VulnBatchDelete(BaseModel):
    """批量删除 CVE 请求体。"""

    ids: list[int] = Field(..., min_length=1, max_length=500, description="要删除的 CVE ID 列表")
