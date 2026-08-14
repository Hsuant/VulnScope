"""插件框架接口契约（方案 §7.3）。

任何 POC 来源（手动/AI/爬取）产出的数据，必须先归一化为 NormalizedPoc（IR），
再进入存储管道。v1 仅定义契约与 IR；注册表/发现机制在 M3 落地。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field

# 合法取值（与存储层应用层校验一致）
POC_SEVERITIES = {"info", "low", "medium", "high", "critical"}
POC_CATEGORIES = {
    "rce",
    "sql-injection",
    "xss",
    "ssti",
    "ssrf",
    "file-upload",
    "lfi",
    "auth-bypass",
    "other",
}
POC_SOURCES = {"manual", "imported", "ai", "crawler"}
POC_FORMATS = {"nuclei-yaml", "json", "pocsuite3", "raw-script"}


class NormalizedPoc(BaseModel):
    """核心与插件之间的稳定中间表示（IR）。content 恒为标准 Nuclei 模板文本。"""

    name: str = Field(pattern=r"^[a-zA-Z0-9一-龥][a-zA-Z0-9一-龥. \-]*$", max_length=128)
    title: str | None = None
    description: str | None = None
    author: str | None = None
    source: str = "manual"
    category: str = "other"
    severity: str = "info"
    content: str  # 模板主体
    format: str = "nuclei-yaml"
    language: str | None = None
    cve_ids: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    references: list[str] = Field(default_factory=list)
    extra_meta: dict[str, Any] = Field(default_factory=dict)

    def validate_structure(self) -> list[str]:
        """结构自检，返回错误列表（空列表 = 合法）。AI 生成模块复用此管道。"""
        errors: list[str] = []
        if not self.name:
            errors.append("name 必填")
        if not self.content:
            errors.append("content 必填")
        elif self.format == "nuclei-yaml" and not self.content.lstrip().startswith(("id:", "info:")):
            errors.append("nuclei 模板必须以 id:/info: 开头")
        if self.severity not in POC_SEVERITIES:
            errors.append(f"非法 severity: {self.severity}")
        if self.category not in POC_CATEGORIES:
            errors.append(f"非法 category: {self.category}")
        if self.source not in POC_SOURCES:
            errors.append(f"非法 source: {self.source}")
        for cve in self.cve_ids:
            if not cve.startswith("CVE-"):
                errors.append(f"非法 CVE 编号: {cve}")
        return errors


class PocSource(ABC):
    """POC 来源插件：手动录入 / AI 生成 / 爬取统一走此接口。"""

    name: str
    version: str

    @abstractmethod
    def fetch(self, params: dict[str, Any]) -> list[NormalizedPoc]:
        """获取/生成一批规范化 POC 数据。"""


class PocParser(ABC):
    """格式解析插件。"""

    name: str = "base-parser"
    supported_formats: set[str] = set()

    @abstractmethod
    def parse(self, raw: str | bytes, format: str | None = None) -> list[NormalizedPoc]:
        """把原始内容解析为规范化 POC。"""

    def validate(self, poc: NormalizedPoc) -> list[str]:
        """模板结构校验（§6.4）。v1 默认仅基础校验，子类可加强。"""
        return poc.validate_structure()


class PocVerifier(ABC):
    """验证引擎插件（v2 实现）。v1 仅定义契约。"""

    name: str
    version: str

    @abstractmethod
    def verify(self, poc: NormalizedPoc, target: str, options: dict[str, Any]) -> dict[str, Any]:
        """对目标执行 POC 验证，返回结构化结果。"""


class PocExporter(ABC):
    """导出插件。"""

    name: str
    supported_formats: set[str] = set()

    @abstractmethod
    def export(self, pocs: list[NormalizedPoc]) -> str:
        """把 POC 列表导出为指定格式文本。"""
