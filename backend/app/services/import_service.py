"""导入导出服务：格式嗅探、解析分发、批量导入、导出。

导入管道（方案 §7.5）：
  文件/URL/文本 → 格式嗅探(FormatDetector) → 分发到对应 Parser 插件
    → 归一化 NormalizedPoc[] → 规范化+hash → validate() → 去重(sha256)
    → 事务入库（含 poc_version 首版本）→ 发布 BATCH_IMPORTED 事件
"""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from typing import Any

import yaml
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.events import DomainEvent, EventTypes, event_bus
from app.core.timeutil import iso_utc
from app.models.poc import Poc, PocTag, PocVersion, PocVuln, Tag, Vuln
from app.plugins.registry import registry
from app.schemas.poc import PocImportResult

# ── 格式嗅探 ──────────────────────────────────────────────────────────


class FormatDetector:
    """格式嗅探器：通过 magic bytes / 扩展名 / YAML 头 / JSON 结构启发式判定格式。"""

    # YAML 起始标记
    YAML_STARTS = {b"id:", b"info:", b"api:", b"id: ", b"info: "}

    # 扩展名映射
    EXTENSION_MAP: dict[str, str] = {
        ".yaml": "nuclei",
        ".yml": "nuclei",
        ".json": "json",
        ".py": "pocsuite3",
        ".go": "raw-script",
        ".rb": "raw-script",
        ".sh": "raw-script",
        ".md": "markdown",
        ".markdown": "markdown",
    }

    # Markdown front-matter 起始分隔符（--- 包裹的 YAML 头）
    _FM_PATTERN = re.compile(r"\A---[ \t]*\r?\n.*?\r?\n---[ \t]*(?:\r?\n|\Z)", re.DOTALL)

    # ATX 标题（# ~ ######），用于无扩展名内容的 Markdown 启发式判定
    _HEADING_PATTERN = re.compile(r"\A#{1,6}[ \t]+")

    @classmethod
    def detect(cls, raw: str | bytes, filename: str | None = None) -> str:
        """检测内容格式，返回格式标识。

        Args:
            raw: 原始内容（str 或 bytes）。
            filename: 可选文件名，用于扩展名辅助判断。

        Returns:
            格式标识：nuclei / json / pocsuite3 / raw-script / markdown
        """
        if isinstance(raw, str):
            raw_bytes = raw.encode("utf-8")
            raw_text = raw
        else:
            raw_bytes = raw
            raw_text = raw.decode("utf-8", errors="replace")

        raw_stripped = raw_bytes.lstrip()
        text_stripped = raw_text.lstrip()

        # 0. 扩展名优先：.md/.markdown 明确为 Markdown（避免被 YAML 兜底误判）
        if filename:
            ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
            if ext in {".md", ".markdown"}:
                return "markdown"

        # 1. 检查 JSON 结构
        if raw_stripped.startswith((b"{", b"[")):
            try:
                json.loads(raw_bytes)
                return "json"
            except (json.JSONDecodeError, ValueError):
                pass

        # 2. 检查 YAML 头
        for start in cls.YAML_STARTS:
            if raw_stripped.startswith(start):
                return "nuclei"

        # 3. 检查 Python 脚本（pocsuite3）
        if raw_stripped.startswith((b"import", b"from", b"#!/usr/bin/env python", b"class ")):
            return "pocsuite3"

        # 4. Markdown 启发式：front-matter 起始 或 顶格 ATX 标题
        #    （#!/bin/bash 等无空格的 # 不在此列，避免误判 shell 脚本）
        if cls._FM_PATTERN.match(text_stripped) or cls._HEADING_PATTERN.match(text_stripped):
            return "markdown"

        # 5. 检查扩展名（其余扩展名映射）
        if filename:
            ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
            if ext in cls.EXTENSION_MAP:
                return cls.EXTENSION_MAP[ext]

        # 6. 再次尝试 YAML 解析兜底
        try:
            yaml.safe_load(raw_bytes)
            return "nuclei"
        except yaml.YAMLError:
            pass

        return "raw-script"


# ── 内容归一化 ──────────────────────────────────────────────────────────


def _normalize_content(content: str) -> str:
    """归一化内容用于 hash 计算。"""
    content = content.strip()
    content = content.replace("\r\n", "\n").replace("\r", "\n")
    content = "\n".join(line.rstrip() for line in content.split("\n"))
    content = content.rstrip("\n") + "\n"
    return content


def _compute_content_hash(content: str) -> str:
    """计算 SHA-256 哈希。"""
    normalized = _normalize_content(content)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


# ── 导入管道 ──────────────────────────────────────────────────────────


def import_pocs(
    db: Session,
    raw_content: str | bytes,
    filename: str | None = None,
    source: str = "imported",
    user_id: int | None = None,
    ip: str | None = None,
    default_status: str = "draft",
) -> PocImportResult:
    """批量导入 POC。

    管道流程：
    1. 格式嗅探
    2. 分发到对应 Parser 插件
    3. 归一化 → hash → validate()
    4. 去重（content_hash）
    5. 事务入库
    6. 发布事件

    Args:
        db: 数据库会话。
        raw_content: 原始内容。
        filename: 可选文件名，辅助格式判断。
        source: 来源类型，默认 "imported"。
        user_id: 操作用户 ID。
        ip: 客户端 IP。
        default_status: 导入后的默认状态。

    Returns:
        PocImportResult 导入结果报告。
    """
    result = PocImportResult()

    # 1. 格式嗅探
    fmt = FormatDetector.detect(raw_content, filename)

    # 2. 分发到 Parser 插件
    normalized_pocs = _parse_content(raw_content, fmt)
    result.total = len(normalized_pocs)

    if not normalized_pocs:
        result.failed.append({"error": f"无法解析为 {fmt} 格式的 POC"})
        return result

    # 3-5. 逐条处理
    for npoc in normalized_pocs:
        try:
            _import_single_poc(db, npoc, fmt, source, user_id, default_status)
            result.success += 1
        except Exception as exc:
            result.failed.append(
                {
                    "name": npoc.name,
                    "error": str(exc),
                }
            )
            result.skipped += 1

    # 6. 发布批量导入事件
    db.commit()
    event_bus.publish(
        DomainEvent(
            event_type=EventTypes.BATCH_IMPORTED.value,
            aggregate_id=None,
            payload={
                "total": result.total,
                "success": result.success,
                "skipped": result.skipped,
                "failed_count": len(result.failed),
                "source": source,
            },
        )
    )

    # 写入审计日志
    if user_id:
        import datetime as dt

        from app.models.poc import AuditLog

        log = AuditLog(
            user_id=user_id,
            action="poc.batch_imported",
            resource_type="poc",
            resource_id="batch",
            detail={
                "total": result.total,
                "success": result.success,
                "skipped": result.skipped,
                "failed": result.failed,
                "source": source,
                "filename": filename,
            },
            ip=ip or "",
            created_at=dt.datetime.now(dt.timezone.utc),
        )
        db.add(log)
        db.commit()

    return result


def _parse_content(raw_content: str | bytes, fmt: str) -> list[Any]:
    """分发到对应 Parser 插件解析内容。"""
    # 先尝试从注册表获取 parser
    parser_entry = registry.get("parser", fmt)
    if parser_entry and parser_entry.enabled:
        try:
            return parser_entry.instance.parse(raw_content, fmt)
        except Exception as exc:
            raise ValueError(f"Parser 插件 '{fmt}' 解析失败: {exc}") from exc

    # 内置兜底解析
    if fmt == "nuclei":
        from app.plugins.parser.nuclei_parser import parser as nuclei_parser

        return nuclei_parser.parse(raw_content, fmt)
    elif fmt == "json":
        from app.plugins.parser.json_parser import parser as json_parser

        return json_parser.parse(raw_content, fmt)
    else:
        # raw-script / pocsuite3 降级为简单包装
        from app.plugins.base import NormalizedPoc

        text = raw_content if isinstance(raw_content, str) else raw_content.decode("utf-8", errors="replace")
        name = _infer_name(text, fmt)
        return [
            NormalizedPoc(
                name=name,
                content=text,
                format=fmt,
                source="imported",
                extra_meta={"format": fmt},
            )
        ]


def _infer_name(text: str, fmt: str) -> str:
    """从内容中推断 POC 名称。"""
    # 尝试从 YAML 提取 id
    if fmt == "nuclei":
        try:
            doc = yaml.safe_load(text)
            if isinstance(doc, dict) and doc.get("id"):
                return str(doc["id"])
        except yaml.YAMLError:
            pass
    # 生成 fallback 名称
    content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]
    return f"imported-{content_hash}"


def _tag_match_key(token: str) -> str:
    """归一化标签 token 为匹配/规范键：去空格、小写、下划线转连字符、去首尾连字符。

    兼容全大写/全小写/混合大小写，以及 ``-`` 与 ``_`` 的差异——
    ``SQL-Injection``、``sql_injection``、``SQL_Injection`` 归一为同一键 ``sql-injection``。
    """
    return token.strip().lower().replace("_", "-").strip("-")


def _resolve_tag(db: Session, tag_str: str) -> Tag:
    """解析导入的标签字符串，自动匹配或创建规范标签。

    匹配策略：
    1. 支持 "namespace:name" 格式解析
    2. 归一化匹配已有标签：小写 + 下划线统一为连字符，跨所有 namespace
       （兼容全大写/全小写/混合大小写，以及 - 与 _ 的差异）
    3. 匹配成功则复用已有标签（保持其 namespace 和 name 原样，即「转换为我们自创建的标签」）
    4. 匹配失败则创建新标签：name 规范化为小写连字符形式；
       namespace 从输入推断，无则默认 "general"

    Args:
        db: 数据库会话。
        tag_str: 导入的标签字符串，可能为 "namespace:name" 或纯 "name"。

    Returns:
        Tag 对象（已 flush 到数据库）。
    """
    tag_str = tag_str.strip()
    if not tag_str:
        raise ValueError("标签名不能为空")

    # 尝试解析 namespace:name 格式
    namespace_hint: str | None = None
    name = tag_str
    if ":" in tag_str:
        parts = tag_str.split(":", 1)
        ns = parts[0].strip()
        nm = parts[1].strip()
        if nm:
            namespace_hint = ns
            name = nm
        # 若冒号后为空（如 "type:"），视作纯 name="type"

    # 归一化匹配键（小写 + 下划线转连字符 + 去首尾连字符）
    name_key = _tag_match_key(name)
    if not name_key:
        raise ValueError("标签名不能为空")

    from sqlalchemy import func

    # 归一化匹配已有标签（跨所有 namespace，兼容大小写与 -/_ 差异）
    existing = db.scalar(select(Tag).where(func.replace(func.lower(Tag.name), "_", "-") == name_key))
    if existing:
        return existing

    # 未匹配到，创建新标签：name 规范化为小写连字符形式
    # 若输入有 namespace_hint 且该 namespace 已存在，沿用之；否则默认 "general"
    final_namespace = "general"
    if namespace_hint:
        ns_key = _tag_match_key(namespace_hint)
        ns_exists = db.scalar(
            select(Tag).where(func.replace(func.lower(Tag.namespace), "_", "-") == ns_key).limit(1)
        )
        if ns_exists:
            final_namespace = ns_exists.namespace  # 保持已有 namespace 原样
        else:
            final_namespace = namespace_hint

    tag = Tag(namespace=final_namespace, name=name_key)
    db.add(tag)
    db.flush()
    return tag


def _sync_vuln_from_poc(vuln: Vuln, npoc: Any) -> None:
    """把 POC 解析出的 CVE 元数据同步到 vuln 记录。

    仅填充目标字段为空的位置，不覆盖已有值；用于「CVE 不存在则创建、
    存在则补缺」的导入联动。同步字段：cvss 评分、cvss_metrics、severity、
    vendor、product、remediation.mitigation。

    Args:
        vuln: 目标 Vuln 记录（新建或已存在）。
        npoc: 已解析的 NormalizedPoc，提供来源元数据。
    """
    if vuln.cvss is None and npoc.cvss_score is not None:
        vuln.cvss = npoc.cvss_score
    if not vuln.cvss_metrics and npoc.cvss_metrics:
        vuln.cvss_metrics = npoc.cvss_metrics
    if not vuln.severity and npoc.severity:
        vuln.severity = npoc.severity
    if not vuln.vendor and npoc.vendor:
        vuln.vendor = npoc.vendor
    if vuln.product is None and npoc.product:
        vuln.product = npoc.product
    if npoc.remediation:
        current = dict(vuln.remediation or {})
        if not current.get("mitigation"):
            current["mitigation"] = npoc.remediation
            vuln.remediation = current


def _import_single_poc(
    db: Session,
    npoc: Any,
    fmt: str,
    source: str,
    user_id: int | None,
    default_status: str,
) -> Poc:
    """导入单条 POC。"""
    content = npoc.content
    content_hash = _compute_content_hash(content)

    # 去重检查
    existing = db.scalar(select(Poc).where(Poc.content_hash == content_hash))
    if existing:
        raise ValueError(f"内容重复: 已存在 '{existing.name}' (id={existing.id})")

    # 名称唯一性检查
    name = npoc.name
    existing_name = db.scalar(select(Poc).where(Poc.name == name, Poc.source == source))
    if existing_name:
        # 自动生成唯一名称
        suffix = content_hash[:8]
        name = f"{name}-{suffix}"

    # 创建 POC
    poc_uuid = str(uuid.uuid4())
    poc = Poc(
        uuid=poc_uuid,
        name=name,
        title=npoc.title or None,
        description=npoc.description or None,
        severity=npoc.severity,
        format=npoc.format,
        content=_normalize_content(content),
        content_hash=content_hash,
        author=npoc.author or None,
        source=source,
        status=default_status,
        version=1,
        extra_meta=npoc.extra_meta or None,
        created_by=user_id,
        updated_by=user_id,
    )
    db.add(poc)
    db.flush()

    # 关联 CVE（不存在则按 POC 元数据自动创建；存在则仅补充空缺字段，不覆盖已有值）
    #   先对 cve_id 去重，避免同一 POC 重复关联（poc_vuln 为复合主键，重复会触发 IntegrityError）
    seen_vuln_ids: set[int] = set()
    for cve_id in npoc.cve_ids:
        cve_id = cve_id.strip().upper()
        if not cve_id:
            continue
        vuln = db.scalar(select(Vuln).where(Vuln.cve_id == cve_id))
        if vuln is None:
            vuln = Vuln(cve_id=cve_id)
            db.add(vuln)
            db.flush()
        _sync_vuln_from_poc(vuln, npoc)
        if vuln.id in seen_vuln_ids:
            continue
        seen_vuln_ids.add(vuln.id)
        db.add(PocVuln(poc_id=poc.id, vuln_id=vuln.id))

    # 关联标签（自动匹配已有标签，不存在的按规范格式创建）
    #   _resolve_tag 跨 namespace/大小写/-与_ 归一匹配，不同写法可能解析到同一 tag.id；
    #   且输入本身可能含重复标签。按 tag.id 去重，避免 poc_tag 复合主键冲突。
    seen_tag_ids: set[int] = set()
    for tag_str in npoc.tags:
        tag_str = tag_str.strip()
        if not tag_str:
            continue
        tag = _resolve_tag(db, tag_str)
        if tag.id in seen_tag_ids:
            continue
        seen_tag_ids.add(tag.id)
        db.add(PocTag(poc_id=poc.id, tag_id=tag.id))

    # 创建首条版本快照
    import datetime as dt

    version = PocVersion(
        poc_id=poc.id,
        version_seq=1,
        content=poc.content,
        content_hash=poc.content_hash,
        changed_by=user_id,
        changed_at=dt.datetime.now(dt.timezone.utc),
    )
    db.add(version)

    # 发布事件
    event_bus.publish(
        DomainEvent(
            event_type=EventTypes.POC_CREATED.value,
            aggregate_id=str(poc.id),
            payload={"name": poc.name, "severity": poc.severity, "source": source},
        )
    )

    return poc


# ── 导出 ──────────────────────────────────────────────────────────────


def export_pocs(db: Session, poc_ids: list[int], export_format: str = "json") -> str:
    """导出 POC 为指定格式。

    Args:
        db: 数据库会话。
        poc_ids: 要导出的 POC ID 列表。
        export_format: 导出格式，json（默认）或 nuclei。

    Returns:
        导出内容的字符串表示。
    """
    from app.models.poc import Poc
    from app.services.poc_service import _load_poc_relations

    pocs = []
    for pid in poc_ids:
        stmt = _load_poc_relations(select(Poc).where(Poc.id == pid))
        poc = db.scalar(stmt)
        if poc:
            pocs.append(poc)

    if export_format == "nuclei":
        return _export_nuclei(pocs)
    else:
        return _export_json(pocs)


def _export_json(pocs: list[Any]) -> str:
    """导出为 JSON 数组格式。"""
    items = []
    for poc in pocs:
        # 提取标签
        tags = []
        if hasattr(poc, "tags") and poc.tags:
            tags = [pt.tag.name for pt in poc.tags if pt.tag]

        # 提取 CVE
        cve_ids = []
        if hasattr(poc, "vulns") and poc.vulns:
            cve_ids = [pv.vuln.cve_id for pv in poc.vulns if pv.vuln]

        items.append(
            {
                "name": poc.name,
                "title": poc.title,
                "description": poc.description,
                "severity": poc.severity,
                "format": poc.format,
                "language": poc.language,
                "content": poc.content,
                "author": poc.author,
                "source": poc.source,
                "status": poc.status,
                "tags": tags,
                "cve_ids": cve_ids,
                "created_at": iso_utc(poc.created_at),
                "updated_at": iso_utc(poc.updated_at),
            }
        )
    return json.dumps(items, ensure_ascii=False, indent=2)


def _export_nuclei(pocs: list[Any]) -> str:
    """导出为 Nuclei YAML 格式（多个模板用 --- 分隔）。"""
    parts = []
    for poc in pocs:
        content = poc.content
        if content:
            content = content.strip()
            if not content.endswith("\n"):
                content += "\n"
            parts.append(content)
    return "---\n".join(parts) + "\n" if parts else ""
