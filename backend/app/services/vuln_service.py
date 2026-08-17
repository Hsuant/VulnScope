"""CVE 漏洞库服务层。"""

from __future__ import annotations

import datetime as dt
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
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


def get_vuln_by_cve_id(db: Session, cve_id: str) -> dict:
    """按 CVE 编号获取漏洞详情。"""
    from sqlalchemy import select as sql_select

    vuln = db.scalar(sql_select(Vuln).where(Vuln.cve_id == cve_id))
    if vuln is None:
        raise NotFoundError("CVE", cve_id)
    poc_count = db.scalar(select(func.count()).select_from(PocVuln).where(PocVuln.vuln_id == vuln.id)) or 0
    return _vuln_to_dict(vuln, poc_count)


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
        "title": vuln.title,
        "description": vuln.description,
        "cvss": vuln.cvss,
        "severity": vuln.severity,
        "poc_count": poc_count,
        "created_at": iso_utc(vuln.created_at) if hasattr(vuln, "created_at") else None,
    }
