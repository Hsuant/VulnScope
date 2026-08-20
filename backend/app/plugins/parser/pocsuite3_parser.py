"""Pocsuite3 Python 脚本解析器。

将 Pocsuite3 格式的 Python POC 脚本解析为 NormalizedPoc IR。
使用正则提取类属性中的结构化字段，无需执行脚本。

支持提取的字段：
- vulID → cve_ids
- name → title
- author → author
- desc → description
- appName/appVersion → product / affected_versions
- references → references
- fofa_syntax / shodan_syntax / publicwww_syntax → extra_meta
- remediation → remediation
- cvss_metrics / cvss_score → cvss_metrics / cvss_score
- cnvd_ids → cnvd_ids
- language → language
"""

from __future__ import annotations

import hashlib
import re
from typing import Any

from app.plugins.base import NormalizedPoc, PocParser

# 合法 severity 值
VALID_SEVERITIES = {"info", "low", "medium", "high", "critical"}

# 正则提取类属性赋值（字符串/列表/数字）
_ATTR_STRING = re.compile(r'^\s+(\w+)\s*=\s*"([^"]*?)"\s*$', re.MULTILINE)
_ATTR_LIST = re.compile(r"^\s+(\w+)\s*=\s*\[([^\]]*?)\]\s*$", re.MULTILINE)
_ATTR_NUMBER = re.compile(r"^\s+(\w+)\s*=\s*([0-9.]+)\s*$", re.MULTILINE)


def _extract_string_attr(text: str, name: str) -> str | None:
    """提取类属性字符串值。"""
    m = re.search(rf"^\s+{name}\s*=\s*\"([^\"]*?)\"\s*$", text, re.MULTILINE)
    if m:
        return m.group(1).strip() or None
    # 也支持三引号
    m = re.search(rf"^\s+{name}\s*=\s*\"\"\"(.*?)\"\"\"", text, re.DOTALL)
    if m:
        return m.group(1).strip() or None
    return None


def _extract_list_attr(text: str, name: str) -> list[str]:
    """提取类属性列表值。"""
    m = re.search(rf"^\s+{name}\s*=\s*\[([^\]]*?)\]\s*$", text, re.MULTILINE)
    if not m:
        return []
    content = m.group(1)
    # 提取引号内的字符串
    items = re.findall(r'"([^"]*?)"', content)
    return [s.strip() for s in items if s.strip()]


def _extract_number_attr(text: str, name: str) -> float | None:
    """提取类属性数值。"""
    m = re.search(rf"^\s+{name}\s*=\s*([0-9.]+)\s*$", text, re.MULTILINE)
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            return None
    return None


def _infer_severity(text: str) -> str:
    """从文本中推断严重级别。"""
    level = _extract_string_attr(text, "level")
    if level and level.lower() in VALID_SEVERITIES:
        return level.lower()
    return "info"


def _infer_name_from_text(text: str) -> str:
    """从文本中推断 POC 名称。"""
    name = _extract_string_attr(text, "name")
    if name:
        slug = name.lower().strip()
        slug = re.sub(r"[^a-zA-Z0-9一-龥. \-]", "-", slug)
        slug = re.sub(r"-{2,}", "-", slug).strip("-")
        if slug:
            return slug[:128]
    # 使用 hash 作为 fallback
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]
    return f"imported-{digest}"


class Pocsuite3Parser(PocParser):
    """Pocsuite3 Python 脚本解析器。"""

    name: str = "pocsuite3"
    supported_formats: set[str] = {"pocsuite3", "py"}

    def parse(self, raw: str | bytes, format: str | None = None) -> list[NormalizedPoc]:
        """解析 Pocsuite3 Python 脚本为 NormalizedPoc 列表。"""
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8", errors="replace")

        return [self._parse_single(raw)]

    def _parse_single(self, text: str) -> NormalizedPoc:
        """解析单个 Python 脚本。"""
        # 提取基本信息
        name = _infer_name_from_text(text)
        title = _extract_string_attr(text, "name")
        author = _extract_string_attr(text, "author")
        description = (
            _extract_string_attr(text, "desc")
            or _extract_string_attr(text, "description")
            or _extract_string_attr(text, "pocDesc")
        )
        severity = _infer_severity(text)

        # 提取 CVE 编号
        cve_ids: list[str] = []
        vul_id = _extract_string_attr(text, "vulID")
        if vul_id:
            upper = vul_id.upper().strip()
            if upper.startswith("CVE-"):
                cve_ids.append(upper)
            else:
                # vulID 可能只是一个名称，检查是否有 CVE 编号嵌入
                cve_match = re.search(r"CVE-\d{4}-\d{4,}", upper)
                if cve_match:
                    cve_ids.append(cve_match.group(0))

        # 提取 CNVD 编号
        cnvd_ids: list[str] = []
        cnvd = _extract_string_attr(text, "cnvdID") or _extract_string_attr(text, "cnvd_ids")
        if cnvd:
            cnvd_ids.append(cnvd.strip())

        # 提取标签
        tags: list[str] = []
        tags_raw = _extract_list_attr(text, "tags")
        if tags_raw:
            tags = [t.strip() for t in tags_raw if t.strip()]
        # 从 vulType 推断标签
        vul_type = _extract_string_attr(text, "vulType")
        if vul_type:
            tags.append(vul_type.lower().replace("_", "-"))

        # 提取参考链接
        references = _extract_list_attr(text, "references")

        # 提取产品信息
        app_name = _extract_string_attr(text, "appName")
        app_version = _extract_string_attr(text, "appVersion")
        app_power_link = _extract_string_attr(text, "appPowerLink")

        product_list: list[dict[str, Any]] | None = None
        if app_name:
            product_list = [{"vendor": app_power_link or "", "product": app_name}]

        # 提取版本影响范围
        affected_versions: list[dict[str, Any]] = []
        if app_version:
            # 解析版本表达式，如 "<=2.14.1" 或 "2.0 ~ 2.14.1"
            ver = app_version.strip()
            av_match = re.match(r"([><=]+)\s*([\d.]+)", ver)
            if av_match:
                op = av_match.group(1)
                v = av_match.group(2)
                if op.startswith("<"):
                    affected_versions.append(
                        {
                            "version_start": None,
                            "version_start_type": "",
                            "version_end": v,
                            "version_end_type": "<=" if "=" in op else "<",
                        }
                    )
                elif op.startswith(">"):
                    affected_versions.append(
                        {
                            "version_start": v,
                            "version_start_type": ">=" if "=" in op else ">",
                            "version_end": None,
                            "version_end_type": "",
                        }
                    )
            elif "~" in ver:
                parts = ver.split("~")
                if len(parts) == 2:
                    affected_versions.append(
                        {
                            "version_start": parts[0].strip(),
                            "version_start_type": ">=",
                            "version_end": parts[1].strip(),
                            "version_end_type": "<=",
                        }
                    )
            else:
                affected_versions.append(
                    {
                        "version_start": None,
                        "version_start_type": "",
                        "version_end": ver,
                        "version_end_type": "<=",
                    }
                )

        # 提取语言
        language = "python"

        # 提取资产探测语法
        extra_meta: dict[str, Any] = {"format": "pocsuite3"}
        fofa = _extract_string_attr(text, "fofa_syntax")
        shodan = _extract_string_attr(text, "shodan_syntax")
        publicwww = _extract_string_attr(text, "publicwww_syntax")
        if fofa:
            extra_meta["fofa_syntax"] = fofa
        if shodan:
            extra_meta["shodan_syntax"] = shodan
        if publicwww:
            extra_meta["publicwww_syntax"] = publicwww

        # 提取修复建议
        remediation = _extract_string_attr(text, "remediation") or _extract_string_attr(text, "solution")

        # 提取 CVSS
        cvss_score = _extract_number_attr(text, "cvss_score") or _extract_number_attr(text, "cvss")
        cvss_metrics = _extract_string_attr(text, "cvss_metrics")

        return NormalizedPoc(
            name=name,
            title=title,
            description=description,
            author=author,
            source="imported",
            severity=severity,
            content=text,
            format="pocsuite3",
            language=language,
            cve_ids=cve_ids,
            cnvd_ids=cnvd_ids,
            tags=tags,
            references=references,
            extra_meta=extra_meta,
            cvss_score=cvss_score,
            cvss_metrics=cvss_metrics,
            remediation=remediation,
            vendor=app_power_link,
            product=product_list,
            affected_versions=affected_versions,
        )


# 注册实例
parser = Pocsuite3Parser()
