"""CVE 漏洞库 API 路由。"""

from __future__ import annotations

from fastapi import APIRouter, Query, Request

from app.api.deps import CurrentUser, DbSession
from app.schemas.common import ok
from app.services import vuln_service

router = APIRouter(prefix="/vulns", tags=["vulns"])


@router.get("")
def list_vulns(
    request: Request,
    db: DbSession,
    user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    severity: str | None = Query(default=None, description="按严重级别筛选"),
    q: str | None = Query(default=None, description="搜索 CVE 编号或标题"),
) -> dict:
    """分页查询 CVE 漏洞库（含每个漏洞的 POC 关联数）。"""
    items, total = vuln_service.list_vulns(db, page=page, page_size=page_size, severity=severity, q=q)
    return ok({"items": items, "total": total}, request)


@router.get("/{vuln_id}")
def get_vuln(
    request: Request,
    db: DbSession,
    user: CurrentUser,
    vuln_id: int,
) -> dict:
    """获取 CVE 漏洞详情（含 POC 关联数）。"""
    vuln = vuln_service.get_vuln(db, vuln_id)
    return ok(vuln, request)


@router.get("/by-cve/{cve_id}")
def get_vuln_by_cve_id(
    request: Request,
    db: DbSession,
    user: CurrentUser,
    cve_id: str,
) -> dict:
    """按 CVE 编号获取漏洞详情。"""
    vuln = vuln_service.get_vuln_by_cve_id(db, cve_id)
    return ok(vuln, request)
