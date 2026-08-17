"""CVE 漏洞库相关 Pydantic schema。"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ReferenceLink(BaseModel):
    """参考链接条目。"""

    url: str
    label: str | None = None


class AffectedProduct(BaseModel):
    """受影响产品条目。"""

    vendor: str | None = None
    product: str | None = None
    version: str | None = None
    version_start: str | None = None
    version_start_type: str | None = None
    version_end: str | None = None
    version_end_type: str | None = None


class Remediation(BaseModel):
    """修复建议。"""

    mitigation: str | None = Field(default=None, description="官方补丁/修复方案")
    workaround: str | None = Field(default=None, description="临时解决方案/规避措施")


class VulnResponse(BaseModel):
    """CVE 漏洞响应体。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    cve_id: str
    vendor: str | None = None
    title: str | None = None
    description: str | None = None
    cvss: float | None = None
    severity: str | None = None
    cvss_metrics: str | None = None
    product: list[AffectedProduct] | None = None
    remediation: Remediation | None = None
    reference: list[ReferenceLink] | None = None
    poc_count: int = 0
    created_at: str | None = None
    updated_at: str | None = None


class VulnList(BaseModel):
    """CVE 列表（含分页）。"""

    items: list[VulnResponse]
    total: int


class VulnCreate(BaseModel):
    """创建 CVE 请求体。"""

    cve_id: str = Field(..., pattern=r"^CVE-\d{4}-\d{4,}$", description="CVE 编号")
    vendor: str | None = Field(default=None, max_length=128, description="厂商（开发该软件的公司/组织）")
    title: str | None = Field(default=None, max_length=255)
    description: str | None = None
    cvss: float | None = Field(default=None, ge=0, le=10)
    severity: str | None = Field(default=None, max_length=16)
    cvss_metrics: str | None = Field(default=None, max_length=255, description="CVSS 指标向量")
    product: list[AffectedProduct] | None = None
    remediation: Remediation | None = None
    reference: list[ReferenceLink] | None = None


class VulnUpdate(BaseModel):
    """更新 CVE 请求体（cve_id 不可修改，不在此列）。"""

    vendor: str | None = Field(default=None, max_length=128, description="厂商（开发该软件的公司/组织）")
    title: str | None = Field(default=None, max_length=255)
    description: str | None = None
    cvss: float | None = Field(default=None, ge=0, le=10)
    severity: str | None = Field(default=None, max_length=16)
    cvss_metrics: str | None = Field(default=None, max_length=255, description="CVSS 指标向量")
    product: list[AffectedProduct] | None = None
    remediation: Remediation | None = None
    reference: list[ReferenceLink] | None = None


class VulnBatchDelete(BaseModel):
    """批量删除 CVE 请求体。"""

    ids: list[int] = Field(..., min_length=1, max_length=500, description="要删除的 CVE ID 列表")


class VulnImportResult(BaseModel):
    """CVE 批量导入结果报告。"""

    total: int = 0
    success: int = 0
    created: int = 0
    updated: int = 0
    skipped: int = 0
    failed: list[dict] = []
