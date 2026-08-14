"""CVE 漏洞库服务层。"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.poc import PocVuln, Vuln


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
        "created_at": (
            vuln.created_at.isoformat() if hasattr(vuln, "created_at") and vuln.created_at else None
        ),
    }
