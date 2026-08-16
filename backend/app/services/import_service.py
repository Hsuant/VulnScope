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

    # 关联 CVE
    for cve_id in npoc.cve_ids:
        cve_id = cve_id.strip().upper()
        if cve_id:
            vuln = db.scalar(select(Vuln).where(Vuln.cve_id == cve_id))
            if vuln is None:
                vuln = Vuln(cve_id=cve_id)
                db.add(vuln)
                db.flush()
            db.add(PocVuln(poc_id=poc.id, vuln_id=vuln.id))

    # 关联标签（按名称匹配/创建）
    for tag_name in npoc.tags:
        tag_name = tag_name.strip()
        if not tag_name:
            continue
        tag = db.scalar(select(Tag).where(Tag.namespace == "general", Tag.name == tag_name))
        if tag is None:
            tag = Tag(namespace="general", name=tag_name)
            db.add(tag)
            db.flush()
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
                "created_at": poc.created_at.isoformat() if poc.created_at else None,
                "updated_at": poc.updated_at.isoformat() if poc.updated_at else None,
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
