"""CVE 批量导入管道。

流程：格式判定 → 解析为 ``NormalizedVuln`` 列表 → 逐条 upsert
（不存在则创建，存在则按「仅补缺」合并）→ 汇总结果报告。
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.events import DomainEvent, EventTypes, event_bus
from app.models.poc import AuditLog, Vuln
from app.schemas.vuln import VulnImportResult
from app.services.vuln_parser import NormalizedVuln, detect_format, from_dict, parse


def import_vulns(
    db: Session,
    raw_content: str | bytes,
    filename: str | None = None,
    user_id: int | None = None,
    ip: str | None = None,
) -> VulnImportResult:
    """批量导入 CVE 漏洞记录。

    自动判定格式（json/jsonl/yaml/markdown）并解析，逐条 upsert：
    cve_id 不存在则创建，存在则仅补充空缺字段（不覆盖已有值）。

    Args:
        db: 数据库会话。
        raw_content: 原始内容（str 或 bytes）。
        filename: 可选文件名，用于格式判定与错误定位。
        user_id: 操作用户 ID，用于审计日志留痕。
        ip: 操作来源 IP，用于审计日志留痕。

    Returns:
        VulnImportResult 导入结果报告（total/created/updated/skipped/failed）。
    """
    result = VulnImportResult()
    label = filename or "(粘贴内容)"

    fmt = detect_format(raw_content, filename)
    try:
        items = parse(raw_content, fmt)
    except ValueError as exc:
        result.total = 1
        result.failed.append({"name": label, "error": f"解析失败({fmt}): {exc}"})
        return result

    result.total = len(items)
    if not items:
        result.failed.append({"name": label, "error": f"未解析到任何 CVE 记录({fmt})"})
        return result

    for item in items:
        name = item.get("cve_id") or item.get("cve") or item.get("id") or "(unknown)"
        try:
            nvuln = from_dict(item)
        except ValueError as exc:
            result.failed.append({"name": str(name), "error": str(exc)})
            continue
        try:
            outcome = _upsert_vuln(db, nvuln, user_id, ip)
        except Exception as exc:  # noqa: BLE001 单条失败不阻塞整批
            result.failed.append({"name": nvuln.cve_id, "error": str(exc)})
            continue
        if outcome == "created":
            result.created += 1
        elif outcome == "updated":
            result.updated += 1
        else:
            result.skipped += 1

    result.success = result.created + result.updated
    db.commit()

    _publish_import_event(result, filename)
    _write_batch_audit_log(db, result, user_id, ip, filename)
    return result


def _upsert_vuln(
    db: Session,
    nvuln: NormalizedVuln,
    user_id: int | None,
    ip: str | None,
) -> str:
    """单条 CVE upsert：创建或补缺。

    Args:
        db: 数据库会话。
        nvuln: 归一化 CVE 记录。
        user_id: 操作用户 ID。
        ip: 操作来源 IP。

    Returns:
        "created" / "updated" / "skipped"（skipped 表示存在且无需补缺）。
    """
    vuln = db.scalar(select(Vuln).where(Vuln.cve_id == nvuln.cve_id))
    if vuln is None:
        vuln = Vuln(cve_id=nvuln.cve_id)
        _apply_all(vuln, nvuln)
        db.add(vuln)
        db.flush()
        _create_audit_log(db, user_id, "vuln.created", vuln, ip)
        return "created"

    if _fill_missing(vuln, nvuln):
        db.flush()
        _create_audit_log(db, user_id, "vuln.updated", vuln, ip)
        return "updated"
    return "skipped"


def _apply_all(vuln: Vuln, nvuln: NormalizedVuln) -> None:
    """将归一化记录的全部字段写入新 vuln 对象。"""
    vuln.vendor = nvuln.vendor
    vuln.title = nvuln.title
    vuln.description = nvuln.description
    vuln.cvss = nvuln.cvss
    vuln.severity = nvuln.severity
    vuln.cvss_metrics = nvuln.cvss_metrics
    vuln.product = nvuln.product
    vuln.remediation = nvuln.remediation
    vuln.reference = nvuln.reference


def _fill_missing(vuln: Vuln, nvuln: NormalizedVuln) -> bool:
    """对已存在 vuln 仅补充空缺字段，不覆盖已有值。

    Args:
        vuln: 已存在漏洞记录。
        nvuln: 归一化记录，提供补缺来源。

    Returns:
        是否发生变更。
    """
    changed = False
    if vuln.cvss is None and nvuln.cvss is not None:
        vuln.cvss = nvuln.cvss
        changed = True
    if not vuln.cvss_metrics and nvuln.cvss_metrics:
        vuln.cvss_metrics = nvuln.cvss_metrics
        changed = True
    if not vuln.severity and nvuln.severity:
        vuln.severity = nvuln.severity
        changed = True
    if not vuln.vendor and nvuln.vendor:
        vuln.vendor = nvuln.vendor
        changed = True
    if not vuln.title and nvuln.title:
        vuln.title = nvuln.title
        changed = True
    if not vuln.description and nvuln.description:
        vuln.description = nvuln.description
        changed = True
    if vuln.product is None and nvuln.product:
        vuln.product = nvuln.product
        changed = True
    changed = _merge_remediation(vuln, nvuln) or changed
    changed = _merge_reference(vuln, nvuln) or changed
    return changed


def _merge_remediation(vuln: Vuln, nvuln: NormalizedVuln) -> bool:
    """合并修复建议：仅补入缺失的 mitigation / workaround 键。"""
    if not nvuln.remediation:
        return False
    current = dict(vuln.remediation or {})
    sub_changed = False
    if not current.get("mitigation") and nvuln.remediation.get("mitigation"):
        current["mitigation"] = nvuln.remediation["mitigation"]
        sub_changed = True
    if not current.get("workaround") and nvuln.remediation.get("workaround"):
        current["workaround"] = nvuln.remediation["workaround"]
        sub_changed = True
    if sub_changed:
        vuln.remediation = current
    return sub_changed


def _merge_reference(vuln: Vuln, nvuln: NormalizedVuln) -> bool:
    """合并参考链接：按 url 去重追加，已有 url 不重复加入。"""
    if not nvuln.reference:
        return False
    existing = vuln.reference or []
    seen = {r.get("url") for r in existing if isinstance(r, dict)}
    merged = list(existing)
    added = False
    for ref in nvuln.reference:
        url = ref.get("url")
        if url and url not in seen:
            seen.add(url)
            merged.append(ref)
            added = True
    if added:
        vuln.reference = merged
    return added


def _create_audit_log(
    db: Session,
    user_id: int | None,
    action: str,
    vuln: Vuln,
    ip: str | None,
) -> None:
    """写入单条 CVE 审计日志。"""
    db.add(
        AuditLog(
            user_id=user_id,
            action=action,
            resource_type="vuln",
            resource_id=str(vuln.id),
            detail={"cve_id": vuln.cve_id, "severity": vuln.severity},
            ip=ip or "",
            created_at=dt.datetime.now(dt.timezone.utc),
        )
    )


def _write_batch_audit_log(
    db: Session,
    result: VulnImportResult,
    user_id: int | None,
    ip: str | None,
    filename: str | None,
) -> None:
    """写入批量导入审计日志（汇总一条）。"""
    if not user_id:
        return
    db.add(
        AuditLog(
            user_id=user_id,
            action="vuln.batch_imported",
            resource_type="vuln",
            resource_id="batch",
            detail={
                "total": result.total,
                "created": result.created,
                "updated": result.updated,
                "skipped": result.skipped,
                "failed_count": len(result.failed),
                "source": filename or "pasted",
            },
            ip=ip or "",
            created_at=dt.datetime.now(dt.timezone.utc),
        )
    )
    db.commit()


def _publish_import_event(result: VulnImportResult, filename: str | None) -> None:
    """发布批量导入事件，触发仪表盘缓存失效等订阅者。"""
    event_bus.publish(
        DomainEvent(
            event_type=EventTypes.VULN_BATCH_IMPORTED.value,
            aggregate_id=None,
            payload={
                "total": result.total,
                "created": result.created,
                "updated": result.updated,
                "skipped": result.skipped,
                "failed_count": len(result.failed),
                "source": filename or "pasted",
            },
        )
    )
