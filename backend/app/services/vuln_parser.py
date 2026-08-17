"""CVE 导入解析器。

将 json / jsonl / yaml / markdown 原文解析为归一化漏洞记录列表。
格式判定与各格式解析相互独立；新增格式只需实现 ``_parse_xxx`` 并在
``_PARSERS`` 中注册。

归一化记录 ``NormalizedVuln`` 为跨格式统一中间表示，仅 ``cve_id`` 必填，
其余字段缺失时为 None，由导入管道按需填充。
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

import yaml

# CVE 编号正则
CVE_PATTERN = re.compile(r"^CVE-\d{4}-\d{4,}$")

# 扩展名 → 格式
_EXTENSION_MAP: dict[str, str] = {
    ".json": "json",
    ".jsonl": "jsonl",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".md": "markdown",
    ".markdown": "markdown",
}

# front-matter 起止分隔符
_FM_PATTERN = re.compile(r"\A---[ \t]*\r?\n.*?\r?\n---[ \t]*(?:\r?\n|\Z)", re.DOTALL)


@dataclass
class NormalizedVuln:
    """归一化 CVE 记录（跨格式统一中间表示）。

    Attributes:
        cve_id: CVE 编号，形如 ``CVE-2021-44228``，必填。
        vendor: 受影响软件的开发厂商。
        title: 漏洞标题。
        description: 漏洞描述（可为 Markdown）。
        cvss: CVSS 评分，0.0 ~ 10.0。
        severity: 严重级别（info/low/medium/high/critical）。
        cvss_metrics: CVSS 指标向量串。
        product: 受影响产品列表，每项为 dict。
        remediation: 修复建议，含 mitigation / workaround 键。
        reference: 参考链接列表，每项为 {url, label}。
    """

    cve_id: str
    vendor: str | None = None
    title: str | None = None
    description: str | None = None
    cvss: float | None = None
    severity: str | None = None
    cvss_metrics: str | None = None
    product: list[dict[str, Any]] | None = None
    remediation: dict[str, Any] | None = None
    reference: list[dict[str, Any]] | None = None


def detect_format(raw: str | bytes, filename: str | None = None) -> str:
    """判定内容格式。

    优先按文件扩展名判定；无扩展名时按内容启发式判定；
    均无法识别时回退为 yaml（YAML 对纯文本与结构化文本兼容性最好）。

    Args:
        raw: 原始内容（str 或 bytes）。
        filename: 可选文件名，用于扩展名辅助判定。

    Returns:
        格式标识：json / jsonl / yaml / markdown。
    """
    text = raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else raw
    stripped = text.lstrip()

    if filename:
        lower = filename.lower()
        for ext, fmt in _EXTENSION_MAP.items():
            if lower.endswith(ext):
                return fmt

    # JSON / JSONL：以 { 或 [ 起首
    if stripped.startswith(("{", "[")):
        try:
            json.loads(text)
            return "json"
        except (json.JSONDecodeError, ValueError):
            pass
        first_line = next((ln for ln in text.splitlines() if ln.strip()), "")
        if first_line.lstrip().startswith("{"):
            try:
                json.loads(first_line)
                return "jsonl"
            except (json.JSONDecodeError, ValueError):
                pass

    # Markdown：front-matter 起首
    if _FM_PATTERN.match(text):
        return "markdown"

    # 兜底为 yaml
    return "yaml"


def parse(raw: str | bytes, fmt: str) -> list[dict[str, Any]]:
    """按指定格式解析原文为 CVE 字典列表。

    仅做格式层面的拆分（每条返回原始 dict），字段归一化与校验由
    ``from_dict`` 在导入服务中逐条执行，从而单条异常不阻塞整批。

    Args:
        raw: 原始内容（str 或 bytes）。
        fmt: 格式标识（由 ``detect_format`` 给出）。

    Returns:
        CVE 字典列表（未经字段归一化）。

    Raises:
        ValueError: 格式不支持，或整体结构非法（语法错误）。
    """
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8", errors="replace")

    parser = _PARSERS.get(fmt)
    if parser is None:
        raise ValueError(f"不支持的格式: {fmt}")
    return parser(raw)


# ── 字段抽取辅助 ───────────────────────────────────────────────────────


def _first(source: dict[str, Any], *keys: str) -> Any:
    """从 source 中按候选键顺序取首个非空值。"""
    for key in keys:
        if key in source and source[key] is not None:
            return source[key]
    return None


def _str(value: Any) -> str | None:
    """转为去空格字符串，空则返回 None。"""
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _float(value: Any) -> float | None:
    """安全转为 float，非数字或 bool 返回 None。"""
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _normalize_product(raw: Any) -> list[dict[str, Any]] | None:
    """将受影响产品原始值归一为 dict 列表。

    接受：dict 列表、字符串列表（视作产品名）、单个 dict。
    """
    if raw is None:
        return None
    if isinstance(raw, dict):
        raw = [raw]
    if not isinstance(raw, list):
        return None
    out: list[dict[str, Any]] = []
    for item in raw:
        if isinstance(item, str):
            name = item.strip()
            if name:
                out.append({"product": name})
        elif isinstance(item, dict):
            out.append(
                {
                    "vendor": _str(item.get("vendor")),
                    "product": _str(item.get("product")),
                    "version": _str(item.get("version")),
                    "version_start": _str(item.get("version_start")),
                    "version_start_type": _str(item.get("version_start_type")),
                    "version_end": _str(item.get("version_end")),
                    "version_end_type": _str(item.get("version_end_type")),
                }
            )
    return out or None


def _normalize_remediation(raw: Any, top: dict[str, Any]) -> dict[str, Any] | None:
    """将修复建议归一为 {mitigation, workaround}。

    接受 remediation 字段为 dict，或顶层 mitigation / workaround 键。
    """
    mitigation = None
    workaround = None
    if isinstance(raw, dict):
        mitigation = _str(_first(raw, "mitigation", "mitigations", "patch"))
        workaround = _str(_first(raw, "workaround", "workarounds"))
    mitigation = mitigation or _str(_first(top, "mitigation", "mitigations"))
    workaround = workaround or _str(_first(top, "workaround", "workarounds"))
    if mitigation or workaround:
        return {"mitigation": mitigation, "workaround": workaround}
    return None


def _normalize_reference(raw: Any) -> list[dict[str, Any]] | None:
    """将参考链接归一为 [{url, label}] 列表。

    接受：字符串列表、{url, label} dict 列表、单个字符串。
    """
    if raw is None:
        return None
    if isinstance(raw, str):
        raw = [raw]
    if isinstance(raw, dict):
        raw = [raw]
    if not isinstance(raw, list):
        return None
    out: list[dict[str, Any]] = []
    for item in raw:
        if isinstance(item, str):
            url = item.strip()
            if url:
                out.append({"url": url, "label": None})
        elif isinstance(item, dict):
            link_url = _str(item.get("url")) or _str(item.get("link"))
            if link_url:
                out.append({"url": link_url, "label": _str(item.get("label"))})
    return out or None


def from_dict(source: dict[str, Any]) -> NormalizedVuln:
    """将单个 CVE dict 抽取为归一化记录。

    支持常见键名变体（cve_id/cve、cvss/cvss_score 等），缺失必填项
    或 cve_id 格式非法时抛 ValueError。

    Args:
        source: 单条 CVE 的字典表示。

    Returns:
        归一化 CVE 记录。

    Raises:
        ValueError: 缺少 cve_id 或格式非法。
    """
    cve_id = _first(source, "cve_id", "cve", "cveId", "id")
    if cve_id is None:
        raise ValueError("缺少 cve_id")
    cve_id = str(cve_id).strip().upper()
    if not CVE_PATTERN.match(cve_id):
        raise ValueError(f"非法 cve_id: {cve_id}")

    return NormalizedVuln(
        cve_id=cve_id,
        vendor=_str(_first(source, "vendor", "vendor_name")),
        title=_str(_first(source, "title", "name", "summary")),
        description=_str(_first(source, "description", "desc", "details")),
        cvss=_float(_first(source, "cvss", "cvss_score", "cvss-score", "cvssScore")),
        severity=_str(_first(source, "severity")),
        cvss_metrics=_str(
            _first(source, "cvss_metrics", "cvss-metrics", "cvssMetrics", "cvss_vector", "vector")
        ),
        product=_normalize_product(_first(source, "product", "affected", "affected_products", "products")),
        remediation=_normalize_remediation(_first(source, "remediation", "remediations"), source),
        reference=_normalize_reference(_first(source, "reference", "references", "refs", "links")),
    )


# ── 各格式解析实现 ─────────────────────────────────────────────────────


def _parse_json(raw: str) -> list[dict[str, Any]]:
    """解析 JSON（单个对象或对象数组）为字典列表。"""
    data = json.loads(raw)
    if isinstance(data, dict):
        data = [data]
    if not isinstance(data, list):
        raise ValueError("JSON 根节点必须是对象或数组")
    return [item for item in data if isinstance(item, dict)]


def _parse_jsonl(raw: str) -> list[dict[str, Any]]:
    """解析 JSONL（每行一个 JSON 对象）为字典列表。"""
    items: list[dict[str, Any]] = []
    for lineno, line in enumerate(raw.splitlines(), start=1):
        text = line.strip()
        if not text:
            continue
        try:
            item = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"第 {lineno} 行 JSON 解析失败: {exc.msg}") from exc
        if isinstance(item, dict):
            items.append(item)
    return items


def _parse_yaml(raw: str) -> list[dict[str, Any]]:
    """解析 YAML（单文档对象或多文档，每文档可为对象或对象列表）为字典列表。"""
    items: list[dict[str, Any]] = []
    for doc in yaml.safe_load_all(raw):
        if isinstance(doc, dict):
            items.append(doc)
        elif isinstance(doc, list):
            for item in doc:
                if isinstance(item, dict):
                    items.append(item)
    return items


def _parse_markdown(raw: str) -> list[dict[str, Any]]:
    """解析 Markdown 文档为单条字典。

    front-matter（``---`` 包裹的 YAML 头）抽取为结构化字段；
    正文整体作为 description（若 front-matter 未提供 description）。
    """
    lines = raw.splitlines()
    if not lines or lines[0].strip() != "---":
        return []
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        return []
    front_text = "\n".join(lines[1:end])
    body = "\n".join(lines[end + 1 :]).strip()
    try:
        loaded = yaml.safe_load(front_text)
    except yaml.YAMLError:
        return []
    front = loaded if isinstance(loaded, dict) else {}
    if not isinstance(front.get("cve_id"), str):
        return []
    if not front.get("description") and body:
        front["description"] = body
    return [front]


# 格式 → 解析函数
_PARSERS: dict[str, Any] = {
    "json": _parse_json,
    "jsonl": _parse_jsonl,
    "yaml": _parse_yaml,
    "markdown": _parse_markdown,
}
