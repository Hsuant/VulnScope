"""CVE 漏洞库 API 路由。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request

from app.api.deps import CurrentUser, DbSession, require_roles
from app.core.security import Role
from app.models.user import User
from app.schemas.common import ok
from app.schemas.vuln import VulnBatchDelete
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


# ── 删除 ────────────────────────────────────────────────────────────────


@router.delete("/{vuln_id}")
def delete_vuln(
    request: Request,
    db: DbSession,
    vuln_id: int,
    user: User = Depends(require_roles(Role.EDITOR, Role.ADMIN)),
) -> dict:
    """删除单个 CVE 漏洞（需要 editor 或 admin 角色）。

    硬删除，级联清理其与 POC 的关联记录（poc_vuln），删除前记录审计日志。

    Args:
        request (Request): 当前请求，用于记录来源 IP。
        db (DbSession): 数据库会话。
        vuln_id (int): 目标漏洞 ID。
        user (User): 断言具备 editor 或 admin 角色。

    Returns:
        dict: 标准响应体，`data.deleted` 恒为 True。
    """
    vuln_service.delete_vuln(db, vuln_id, user.id, request.client.host if request.client else None)
    return ok({"deleted": True}, request)


@router.delete("")
def delete_vulns_batch(
    request: Request,
    db: DbSession,
    body: VulnBatchDelete,
    user: User = Depends(require_roles(Role.EDITOR, Role.ADMIN)),
) -> dict:
    """批量删除 CVE 漏洞（需要 editor 或 admin 角色）。

    硬删除所选漏洞并级联清理其与 POC 的关联记录；不存在的 ID 静默跳过。

    Args:
        request (Request): 当前请求，用于记录来源 IP。
        db (DbSession): 数据库会话。
        body (VulnBatchDelete): 待删除的漏洞 ID 列表（1~500 个）。
        user (User): 断言具备 editor 或 admin 角色。

    Returns:
        dict: 标准响应体，`data.deleted_count` 为实际删除的漏洞数量。
    """
    deleted_count = vuln_service.delete_vulns_batch(
        db, body.ids, user.id, request.client.host if request.client else None
    )
    return ok({"deleted_count": deleted_count}, request)
