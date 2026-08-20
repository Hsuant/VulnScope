"""Markdown 文档解析器（方案 A：MD 作为 POC 内容格式）。

将带 YAML front-matter 的 Markdown 文档解析为 NormalizedPoc IR。
front-matter 中的 name/title/severity/author/cve/tags/references 映射到
结构化字段，正文（含/不含 front-matter）整体作为 content 存储。

约定 front-matter 形如：

    ---
    title: Apache Log4j2 JNDI RCE
    severity: critical
    author: security-team
    cve:
      - CVE-2021-44228
    tags: [rce, log4j, java]
    references:
      - https://example.com/advisory
    ---

    # 漏洞概述
    正文内容……

无 front-matter 时，从首个一级标题推断 name，正文整体作为 content。
"""

from __future__ import annotations

import hashlib
import re
from typing import Any

import yaml

from app.plugins.base import NormalizedPoc, PocParser

# 合法 severity 值
VALID_SEVERITIES = {"info", "low", "medium", "high", "critical"}

# 与 poc.name 约束一致：字母/数字/汉字开头，允许字母数字汉字点空格连字符
_NAME_DISALLOWED = re.compile(r"[^a-zA-Z0-9一-龥. \-]")

# front-matter 起始分隔符
_FM_PATTERN = re.compile(r"\A---[ \t]*\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|\Z)", re.DOTALL)

# 首个 ATX 一级标题
_H1_PATTERN = re.compile(r"^#{1}[ \t]+(.+?)\s*$", re.MULTILINE)

# 内容长度上限（防超大文档打爆渲染/存储）
_MAX_CONTENT_LEN = 200_000


def _slugify(text: str) -> str:
    """把任意文本归一化为符合 poc.name 正则的 slug。

    规则：小写、非法字符替换为连字符、折叠连续连字符、去首尾连字符；
    中文/字母/数字/点保留。空结果返回 "markdown"。
    """
    text = text.strip().lower()
    text = _NAME_DISALLOWED.sub("-", text)
    text = re.sub(r"-{2,}", "-", text)
    text = text.strip("-")
    if not text:
        return "markdown"
    return text[:128]


class MarkdownParser(PocParser):
    """Markdown 文档解析器。

    支持有/无 front-matter 的 .md 文档；front-matter 字段映射到 NormalizedPoc，
    正文原样保留为 content（format=markdown）。
    """

    name: str = "markdown"
    supported_formats: set[str] = {"markdown", "md"}

    def parse(self, raw: str | bytes, format: str | None = None) -> list[NormalizedPoc]:
        """解析 Markdown 文本为单条 NormalizedPoc。"""
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8", errors="replace")

        front, _ = self._split_front_matter(raw)
        meta: dict[str, Any] = {}
        if front:
            try:
                loaded = yaml.safe_load(front)
                if isinstance(loaded, dict):
                    meta = loaded
            except yaml.YAMLError:
                pass

        return [self._build(meta, raw)]

    def validate(self, poc: NormalizedPoc) -> list[str]:
        """Markdown 专项校验：仅基础非空 + 长度上限，不套脚本格式约束。"""
        errors: list[str] = []
        if not poc.name:
            errors.append("name 必填")
        if not poc.content or not poc.content.strip():
            errors.append("content 必填")
        elif len(poc.content) > _MAX_CONTENT_LEN:
            errors.append(f"内容过长（>{_MAX_CONTENT_LEN} 字符）")
        if poc.severity not in VALID_SEVERITIES:
            errors.append(f"非法 severity: {poc.severity}")
        return errors

    # ── 内部辅助 ────────────────────────────────────────────────────

    def _split_front_matter(self, raw: str) -> tuple[str, str]:
        """拆分 YAML front-matter 与正文，返回 (front, body)。无则 ("", raw)。"""
        m = _FM_PATTERN.match(raw)
        if not m:
            return "", raw
        front = m.group(1)
        end = m.end()
        body = raw[end:]
        return front, body

    def _build(self, meta: dict[str, Any], body: str) -> NormalizedPoc:
        """从 front-matter + 正文构建 NormalizedPoc。"""
        name = self._extract_name(meta, body)
        title = meta.get("title") or meta.get("name")
        description = meta.get("description") or meta.get("summary")
        author = meta.get("author")
        severity = self._norm_severity(meta.get("severity"))
        cve_ids = self._extract_cves(meta)
        tags = self._extract_tags(meta)
        references = self._extract_references(meta)
        fofa = meta.get("fofa_syntax")
        shodan = meta.get("shodan_syntax")
        publicwww = meta.get("publicwww_syntax") or meta.get("publicwww-query") or meta.get("publicwww")

        # 结构化元数据存入 extra_meta
        extra_meta: dict[str, Any] = {}
        if references:
            extra_meta["references"] = references
        if fofa:
            extra_meta["fofa_syntax"] = str(fofa).strip()
        if shodan:
            extra_meta["shodan_syntax"] = str(shodan).strip()
        if publicwww:
            extra_meta["publicwww_syntax"] = str(publicwww).strip()

        # 提取 CNVD/CNNVD 编号
        cnvd_ids: list[str] = []
        cnvd_raw = meta.get("cnvd") or meta.get("cnvd_ids") or meta.get("cnvd_id") or []
        if isinstance(cnvd_raw, str):
            cnvd_raw = [cnvd_raw]
        if isinstance(cnvd_raw, list):
            cnvd_ids = [str(c).strip() for c in cnvd_raw if c and str(c).strip()]

        # 提取版本影响范围
        affected_versions: list[dict[str, Any]] = []
        av_raw = meta.get("affected_versions") or []
        if isinstance(av_raw, list):
            for av in av_raw:
                if isinstance(av, dict):
                    affected_versions.append(
                        {
                            "version_start": av.get("version_start"),
                            "version_start_type": av.get("version_start_type", ">="),
                            "version_end": av.get("version_end"),
                            "version_end_type": av.get("version_end_type", "<="),
                        }
                    )

        # 提取脚本语言
        language = meta.get("language") or None

        # 提取 CVSS 与修复建议
        cvss_metrics = meta.get("cvss_metrics") or None
        remediation = meta.get("remediation") or None

        # 提取厂商/产品
        vendor = meta.get("vendor") or None
        product_raw = meta.get("product") or []
        product_list: list[dict[str, Any]] | None = None
        if isinstance(product_raw, list):
            product_list = []
            for p in product_raw:
                if isinstance(p, dict):
                    product_list.append(
                        {
                            "vendor": p.get("vendor"),
                            "product": p.get("product"),
                            "version": p.get("version"),
                            "version_start": p.get("version_start"),
                            "version_start_type": p.get("version_start_type"),
                            "version_end": p.get("version_end"),
                            "version_end_type": p.get("version_end_type"),
                        }
                    )
        elif isinstance(product_raw, dict):
            product_list = [
                {
                    "vendor": product_raw.get("vendor"),
                    "product": product_raw.get("product"),
                    "version": product_raw.get("version"),
                    "version_start": product_raw.get("version_start"),
                    "version_start_type": product_raw.get("version_start_type"),
                    "version_end": product_raw.get("version_end"),
                    "version_end_type": product_raw.get("version_end_type"),
                }
            ]

        return NormalizedPoc(
            name=name,
            title=str(title) if title else None,
            description=str(description) if description else None,
            author=str(author) if author else None,
            source="imported",
            severity=severity,
            content=body,
            format="markdown",
            language=language,
            cve_ids=cve_ids,
            cnvd_ids=cnvd_ids,
            tags=tags,
            references=[r["url"] for r in references if r.get("url")],
            extra_meta=extra_meta,
            cvss_metrics=cvss_metrics,
            remediation=remediation,
            vendor=vendor,
            product=product_list,
            affected_versions=affected_versions,
        )

    def _extract_name(self, meta: dict[str, Any], body: str) -> str:
        """推断 POC 名称：front-matter.name → 首个 H1 → markdown-<hash8>。"""
        candidate = ""
        raw_name = meta.get("name") or meta.get("id") or meta.get("slug")
        if raw_name:
            candidate = str(raw_name)
        else:
            m = _H1_PATTERN.search(body)
            if m:
                candidate = m.group(1)
        name = _slugify(candidate) if candidate else ""
        if not name or name == "markdown":
            digest = hashlib.sha256(body.encode("utf-8")).hexdigest()[:8]
            name = f"markdown-{digest}"
        return name

    def _norm_severity(self, value: Any) -> str:
        if value is None:
            return "info"
        s = str(value).strip().lower()
        return s if s in VALID_SEVERITIES else "info"

    def _extract_cves(self, meta: dict[str, Any]) -> list[str]:
        """从多种 front-matter 键提取 CVE 编号。"""
        raw = meta.get("cve") or meta.get("cves") or meta.get("cve_id") or meta.get("cve-id") or []
        if isinstance(raw, str):
            raw = [raw]
        if not isinstance(raw, list):
            return []
        out: list[str] = []
        for item in raw:
            s = str(item).strip().upper()
            if s.startswith("CVE-"):
                out.append(s)
        return out

    def _extract_tags(self, meta: dict[str, Any]) -> list[str]:
        raw = meta.get("tags") or meta.get("tag")
        if isinstance(raw, str):
            return [t.strip() for t in raw.split(",") if t.strip()]
        if isinstance(raw, list):
            return [str(t).strip() for t in raw if str(t).strip()]
        return []

    def _extract_references(self, meta: dict[str, Any]) -> list[dict[str, Any]]:
        """提取参考链接，归一化为 [{url, label}]。"""
        raw = meta.get("references", [])
        if isinstance(raw, str):
            raw = [raw]
        if not isinstance(raw, list):
            return []
        from app.plugins.base import normalize_references

        return normalize_references(raw)


# 注册实例（registry 自动扫描发现）
parser = MarkdownParser()
