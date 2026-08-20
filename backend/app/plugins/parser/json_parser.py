"""自研 JSON 格式解析器（兼容导入）。

将自研结构化 JSON 解析为 NormalizedPoc IR。
JSON 格式见 templates/poc/poc.schema.json。
"""

from __future__ import annotations

import json
from typing import Any

from app.plugins.base import NormalizedPoc, PocParser

# 合法值映射
_SEVERITY_MAP = {"1": "low", "2": "medium", "3": "high", "4": "critical", "5": "critical"}


def _coerce_float(value: Any) -> float | None:
    """把任意值安全转为 float，失败返回 None。"""
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


class JsonParser(PocParser):
    """自研 JSON 格式解析器。"""

    name: str = "json-parser"
    supported_formats: set[str] = {"json"}

    def parse(self, raw: str | bytes, format: str | None = None) -> list[NormalizedPoc]:
        """解析 JSON 文本为 NormalizedPoc 列表。

        Args:
            raw: JSON 文本。支持单条对象或对象数组。
            format: 格式标识。

        Returns:
            NormalizedPoc 列表。
        """
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8", errors="replace")

        data = json.loads(raw)
        if isinstance(data, dict):
            data = [data]
        if not isinstance(data, list):
            raise ValueError("JSON 根节点必须是对象或数组")

        return [self._parse_single(item) for item in data]

    def _parse_single(self, item: dict[str, Any]) -> NormalizedPoc:
        """解析单个 JSON 对象。"""
        name = str(item.get("name", ""))
        if not name:
            raise ValueError("JSON POC 缺少 name 字段")

        # 严重级别映射
        severity_raw = item.get("severity", "info")
        if isinstance(severity_raw, int):
            severity = _SEVERITY_MAP.get(str(severity_raw), "info")
        else:
            severity = str(severity_raw).lower()
            if severity not in {"info", "low", "medium", "high", "critical"}:
                severity = "info"

        # 提取内容
        content = item.get("content", "")
        if not content:
            # 尝试从请求/响应结构构建内容
            content = self._build_nuclei_template(item) or ""

        # 提取 CVE
        cve_ids: list[str] = []
        vulns = item.get("vulnerabilities", []) or item.get("cve_ids", []) or []
        if isinstance(vulns, list):
            for v in vulns:
                if isinstance(v, str) and v.upper().startswith("CVE-"):
                    cve_ids.append(v.upper())
                elif isinstance(v, dict):
                    cve_id = v.get("cve_id", "") or v.get("id", "")
                    if cve_id.upper().startswith("CVE-"):
                        cve_ids.append(cve_id.upper())

        # 提取标签
        tags: list[str] = []
        tags_raw = item.get("tags", []) or []
        if isinstance(tags_raw, list):
            tags = [str(t) for t in tags_raw if t]
        elif isinstance(tags_raw, str):
            tags = [t.strip() for t in tags_raw.split(",") if t.strip()]

        from app.plugins.base import normalize_references

        references_norm = normalize_references(item.get("references", []) or [])
        extra_meta: dict[str, Any] = {"original_format": "json"}
        if references_norm:
            extra_meta["references"] = references_norm

        # 解析资产探测语法：metadata 块（构建器写入 fofa-query / shodan-query / publicwww-query），
        # 同时兼容顶层 fofa_syntax / shodan_syntax / publicwww_syntax 等键名变体
        meta = item.get("metadata") or {}
        if isinstance(meta, dict):
            for src_key, dst_key in (("fofa-query", "fofa_syntax"), ("shodan-query", "shodan_syntax")):
                if meta.get(src_key):
                    extra_meta[dst_key] = str(meta[src_key]).strip()
            pub = meta.get("publicwww-query") or meta.get("publicwww") or meta.get("publicwww_syntax")
            if pub:
                extra_meta["publicwww_syntax"] = str(pub).strip()
        for dst_key in ("fofa_syntax", "shodan_syntax", "publicwww_syntax"):
            if dst_key in extra_meta:
                continue
            if item.get(dst_key):
                extra_meta[dst_key] = str(item[dst_key]).strip()

        # 提取 CNVD/CNNVD 编号
        cnvd_ids: list[str] = []
        cnvd_raw = item.get("cnvd_ids") or item.get("cnvd") or []
        if isinstance(cnvd_raw, str):
            cnvd_raw = [cnvd_raw]
        if isinstance(cnvd_raw, list):
            cnvd_ids = [str(c).strip() for c in cnvd_raw if c and str(c).strip()]

        # 提取版本影响范围
        affected_versions: list[dict[str, Any]] = []
        av_raw = item.get("affected_versions") or []
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
        language = item.get("language") or None

        # 提取 CVSS 元数据
        cvss_score = _coerce_float(item.get("cvss_score"))
        cvss_metrics = item.get("cvss_metrics") or None

        # 提取修复建议
        remediation = item.get("remediation") or None

        # 提取厂商/产品
        vendor = item.get("vendor") or None
        product_raw = item.get("product") or []
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

        return NormalizedPoc(
            name=name,
            title=item.get("title") or None,
            description=item.get("description") or None,
            author=item.get("author") or None,
            source="imported",
            severity=severity,
            content=content or f"id: {name}\n\ninfo:\n  name: {name}\n  severity: {severity}\n",
            format="nuclei" if content else "json",
            language=language,
            cve_ids=cve_ids,
            cnvd_ids=cnvd_ids,
            tags=tags,
            references=[r["url"] for r in references_norm if r.get("url")],
            extra_meta=extra_meta,
            cvss_score=cvss_score,
            cvss_metrics=cvss_metrics,
            remediation=remediation,
            vendor=vendor,
            product=product_list,
            affected_versions=affected_versions,
        )

    def _build_nuclei_template(self, item: dict[str, Any]) -> str:
        """从 JSON 字段尝试构建 Nuclei 模板。"""
        name = item.get("name", "unknown")
        severity = str(item.get("severity", "info")).lower()
        description = item.get("description", "")

        lines = [
            f"id: {name}",
            "",
            "info:",
            f"  name: \"{item.get('title', name)}\"",
            f"  severity: {severity}",
        ]
        if description:
            lines.append(f'  description: "{description}"')

        # 如果没有 http 请求信息，返回空
        request = item.get("request", {}) or {}
        if request.get("method") and request.get("path"):
            lines.extend(
                [
                    "",
                    "http:",
                    f"  - method: {request['method']}",
                    "    path:",
                    f"      - \"{{{{BaseURL}}}}{request['path']}\"",
                ]
            )
            return "\n".join(lines) + "\n"

        return ""


# 注册实例
parser = JsonParser()
