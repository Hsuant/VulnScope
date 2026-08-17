"""CVE 漏洞库服务层。"""

from __future__ import annotations

import datetime as dt
import json
from typing import Any

import yaml
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import AppError, ErrorCode, NotFoundError
from app.core.timeutil import iso_utc
from app.models.poc import AuditLog, PocVuln, Vuln


def list_vulns(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 20,
    severity: str | None = None,
    q: str | None = None,
) -> tuple[list[dict], int]:
    """分页查询 CVE 漏洞列表，含每个漏洞关联的 POC 数量。"""
    query = select(Vuln)

    if severity:
        query = query.where(Vuln.severity == severity)
    if q:
        like_pattern = f"%{q}%"
        query = query.where(Vuln.cve_id.ilike(like_pattern) | Vuln.title.ilike(like_pattern))

    # 总数
    count_query = (
        select(func.count()).select_from(Vuln).where(query.whereclause)
        if query.whereclause is not None
        else select(func.count()).select_from(Vuln)
    )
    total = db.scalar(count_query) or 0

    # 分页
    offset = (page - 1) * page_size
    vulns = db.scalars(query.order_by(Vuln.created_at.desc()).offset(offset).limit(page_size)).all()

    # 统计 POC 数量
    result = []
    for vuln in vulns:
        poc_count = (
            db.scalar(select(func.count()).select_from(PocVuln).where(PocVuln.vuln_id == vuln.id)) or 0
        )
        result.append(_vuln_to_dict(vuln, poc_count))

    return result, total


def get_vuln(db: Session, vuln_id: int) -> dict:
    """获取 CVE 详情（含 POC 数量）。"""
    vuln = db.get(Vuln, vuln_id)
    if vuln is None:
        raise NotFoundError("CVE", str(vuln_id))
    poc_count = db.scalar(select(func.count()).select_from(PocVuln).where(PocVuln.vuln_id == vuln.id)) or 0
    return _vuln_to_dict(vuln, poc_count)


def update_vuln(
    db: Session,
    vuln_id: int,
    data: dict[str, Any],
    user_id: int | None = None,
    ip: str | None = None,
) -> dict:
    """更新 CVE 可编辑字段（cve_id 不可修改）。

    接收已校验的字段字典（由 API 层从 VulnUpdate schema 转换而来），
    覆盖式写入各字段（None 表示清空），写入审计日志后提交。

    Args:
        db: 数据库会话。
        vuln_id: 目标漏洞 ID。
        data: 待更新字段字典，键为 vuln 可编辑字段。
        user_id: 操作用户 ID，用于审计日志留痕。
        ip: 操作来源 IP，用于审计日志留痕。

    Returns:
        dict: 更新后的漏洞详情（含 POC 关联数）。

    Raises:
        NotFoundError: 漏洞不存在时抛出。
    """
    vuln = db.get(Vuln, vuln_id)
    if vuln is None:
        raise NotFoundError("CVE", str(vuln_id))

    vuln.vendor = data.get("vendor")
    vuln.title = data.get("title")
    vuln.description = data.get("description")
    vuln.cvss = data.get("cvss")
    vuln.severity = data.get("severity")
    vuln.cvss_metrics = data.get("cvss_metrics")
    vuln.product = data.get("product")
    vuln.remediation = data.get("remediation")
    vuln.reference = data.get("reference")

    _create_audit_log(
        db,
        user_id,
        "vuln.updated",
        "vuln",
        str(vuln.id),
        {"cve_id": vuln.cve_id, "severity": vuln.severity},
        ip,
    )
    db.commit()
    db.refresh(vuln)
    poc_count = db.scalar(select(func.count()).select_from(PocVuln).where(PocVuln.vuln_id == vuln.id)) or 0
    return _vuln_to_dict(vuln, poc_count)


def get_vuln_by_cve_id(db: Session, cve_id: str) -> dict:
    """按 CVE 编号获取漏洞详情。"""
    from sqlalchemy import select as sql_select

    vuln = db.scalar(sql_select(Vuln).where(Vuln.cve_id == cve_id))
    if vuln is None:
        raise NotFoundError("CVE", cve_id)
    poc_count = db.scalar(select(func.count()).select_from(PocVuln).where(PocVuln.vuln_id == vuln.id)) or 0
    return _vuln_to_dict(vuln, poc_count)


def create_vuln(
    db: Session,
    data: dict[str, Any],
    user_id: int | None = None,
    ip: str | None = None,
) -> dict:
    """创建 CVE 漏洞记录。

    cve_id 唯一，重复时抛 CONFLICT(409)。创建后写入审计日志并提交。

    Args:
        db: 数据库会话。
        data: 已校验字段字典（由 API 层从 VulnCreate schema 转换而来）。
        user_id: 操作用户 ID，用于审计日志留痕。
        ip: 操作来源 IP，用于审计日志留痕。

    Returns:
        dict: 新建的漏洞详情（POC 关联数为 0）。

    Raises:
        AppError(CONFLICT): cve_id 已存在时抛出。
    """
    cve_id = data.get("cve_id")
    existing = db.scalar(select(Vuln).where(Vuln.cve_id == cve_id))
    if existing is not None:
        raise AppError(
            ErrorCode.CONFLICT,
            message=f"CVE 已存在: {cve_id}",
            detail={"cve_id": cve_id},
        )

    vuln = Vuln(
        cve_id=cve_id,
        vendor=data.get("vendor"),
        title=data.get("title"),
        description=data.get("description"),
        cvss=data.get("cvss"),
        severity=data.get("severity"),
        cvss_metrics=data.get("cvss_metrics"),
        product=data.get("product"),
        remediation=data.get("remediation"),
        reference=data.get("reference"),
    )
    db.add(vuln)
    db.flush()
    _create_audit_log(db, user_id, "vuln.created", "vuln", str(vuln.id), {"cve_id": vuln.cve_id}, ip)
    db.commit()
    db.refresh(vuln)
    return _vuln_to_dict(vuln, 0)


def delete_vuln(db: Session, vuln_id: int, user_id: int | None = None, ip: str | None = None) -> None:
    """删除单个 CVE 漏洞（硬删除）。

    级联清理 PocVuln 关联记录（依赖 Vuln.pocs 的 cascade="all, delete-orphan"），
    删除前写入审计日志，删除操作与日志在同一事务中提交。

    Args:
        db (Session): 数据库会话。
        vuln_id (int): 目标漏洞 ID。
        user_id (int | None): 操作用户 ID，用于审计日志留痕。
        ip (str | None): 操作来源 IP，用于审计日志留痕。

    Raises:
        NotFoundError: 漏洞不存在时抛出。
    """
    vuln = db.get(Vuln, vuln_id)
    if vuln is None:
        raise NotFoundError("CVE", str(vuln_id))

    _create_audit_log(
        db,
        user_id,
        "vuln.deleted",
        "vuln",
        str(vuln.id),
        {"cve_id": vuln.cve_id, "severity": vuln.severity},
        ip,
    )
    db.delete(vuln)
    db.commit()


def delete_vulns_batch(
    db: Session, vuln_ids: list[int], user_id: int | None = None, ip: str | None = None
) -> int:
    """批量删除 CVE 漏洞（硬删除）。

    先级联清理 PocVuln 关联记录，再删除漏洞本体；已存在的 ID 被删除，
    不存在的 ID 静默跳过，返回实际删除的数量。每个被删除的漏洞写入一条审计日志。

    Args:
        db (Session): 数据库会话。
        vuln_ids (list[int]): 待删除的漏洞 ID 列表（内部去重）。
        user_id (int | None): 操作用户 ID，用于审计日志留痕。
        ip (str | None): 操作来源 IP，用于审计日志留痕。

    Returns:
        int: 实际执行删除的漏洞数量。
    """
    ids = list(dict.fromkeys(vuln_ids))  # 去重并保持原始顺序
    if not ids:
        return 0

    existing = db.scalars(select(Vuln).where(Vuln.id.in_(ids))).all()
    if not existing:
        return 0

    deleted_ids = [v.id for v in existing]
    for vuln in existing:
        _create_audit_log(
            db,
            user_id,
            "vuln.deleted",
            "vuln",
            str(vuln.id),
            {"cve_id": vuln.cve_id, "severity": vuln.severity},
            ip,
        )

    db.query(PocVuln).where(PocVuln.vuln_id.in_(deleted_ids)).delete(synchronize_session=False)
    db.query(Vuln).where(Vuln.id.in_(deleted_ids)).delete(synchronize_session=False)
    db.commit()
    return len(deleted_ids)


def _create_audit_log(
    db: Session,
    user_id: int | None,
    action: str,
    resource_type: str,
    resource_id: str | None,
    detail: dict[str, Any] | None = None,
    ip: str | None = None,
) -> None:
    """写入审计日志记录。

    Args:
        db (Session): 数据库会话。
        user_id (int | None): 操作用户 ID，可为空（如系统操作）。
        action (str): 操作动作标识，如 `vuln.deleted`。
        resource_type (str): 资源类型，如 `vuln`。
        resource_id (str | None): 资源 ID 字符串。
        detail (dict[str, Any] | None): 附加详情（如 CVE 编号）。
        ip (str | None): 操作来源 IP。
    """
    log = AuditLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        detail=detail,
        ip=ip or "",
        created_at=dt.datetime.now(dt.timezone.utc),
    )
    db.add(log)


def _vuln_to_dict(vuln: Vuln, poc_count: int = 0) -> dict:
    """将 Vuln ORM 对象转为字典。"""
    return {
        "id": vuln.id,
        "cve_id": vuln.cve_id,
        "vendor": vuln.vendor,
        "title": vuln.title,
        "description": vuln.description,
        "cvss": vuln.cvss,
        "severity": vuln.severity,
        "cvss_metrics": vuln.cvss_metrics,
        "product": vuln.product,
        "remediation": vuln.remediation,
        "reference": vuln.reference,
        "poc_count": poc_count,
        "created_at": iso_utc(vuln.created_at) if hasattr(vuln, "created_at") else None,
        "updated_at": iso_utc(vuln.updated_at) if hasattr(vuln, "updated_at") else None,
    }


def _vuln_export_dict(vuln: Vuln) -> dict:
    """构造导出用 CVE 字典，字段与导入模板对齐，便于再导入。"""
    return {
        "cve_id": vuln.cve_id,
        "vendor": vuln.vendor,
        "title": vuln.title,
        "description": vuln.description,
        "cvss": vuln.cvss,
        "severity": vuln.severity,
        "cvss_metrics": vuln.cvss_metrics,
        "product": vuln.product,
        "remediation": vuln.remediation,
        "reference": vuln.reference,
    }


def export_vulns(db: Session, vuln_ids: list[int], export_format: str = "json") -> str:
    """导出指定 CVE 为 JSON 或 YAML 文本。

    Args:
        db: 数据库会话。
        vuln_ids: 要导出的漏洞 ID 列表。
        export_format: 导出格式，json（默认）或 yaml。

    Returns:
        导出内容的字符串表示。
    """
    vulns = db.scalars(select(Vuln).where(Vuln.id.in_(vuln_ids))).all()
    records = [_vuln_export_dict(v) for v in vulns]
    if export_format == "yaml":
        return yaml.safe_dump(records, allow_unicode=True, sort_keys=False)
    return json.dumps(records, ensure_ascii=False, indent=2)
