"""CVE 漏洞库 API 路由。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile

from app.api.deps import CurrentUser, DbSession, require_roles
from app.core.exceptions import AppError, ErrorCode
from app.core.security import Role
from app.models.user import User
from app.schemas.common import ok
from app.schemas.vuln import VulnBatchDelete, VulnCreate, VulnUpdate
from app.services import vuln_import_service, vuln_service

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


@router.get("/export")
def export_vulns(
    request: Request,
    db: DbSession,
    user: CurrentUser,
    ids: str = Query(..., description="CVE ID 列表（逗号分隔）"),
    format: str = Query(default="json", description="导出格式: json / yaml"),
) -> dict:
    """导出 CVE 为 JSON 或 YAML 文本。

    JSON 输出对象数组（含完整字段，可再导入）；YAML 输出列表。

    Args:
        request: 当前请求。
        db: 数据库会话。
        user: 当前用户（需认证）。
        ids: 待导出的漏洞 ID 列表（逗号分隔）。
        format: 导出格式，json（默认）或 yaml。

    Returns:
        dict: 标准响应体，data 含 content / format / count。
    """
    vuln_ids = [int(x.strip()) for x in ids.split(",") if x.strip()]
    if not vuln_ids:
        return ok({"content": "", "format": format, "count": 0}, request)
    content = vuln_service.export_vulns(db, vuln_ids, export_format=format)
    return ok({"content": content, "format": format, "count": len(vuln_ids)}, request)


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


@router.post("", status_code=200)
def create_vuln(
    request: Request,
    db: DbSession,
    body: VulnCreate,
    user: User = Depends(require_roles(Role.EDITOR, Role.ADMIN)),
) -> dict:
    """创建 CVE 漏洞记录（需要 editor 或 admin 角色）。

    cve_id 唯一，重复时返回 409。创建后记录审计日志。

    Args:
        request: 当前请求，用于记录来源 IP。
        db: 数据库会话。
        body: CVE 创建字段（VulnCreate），cve_id 须匹配 ^CVE-\\d{4}-\\d{4,}$。
        user: 断言具备 editor 或 admin 角色。

    Returns:
        dict: 标准响应体，data 为新建的漏洞详情。
    """
    vuln = vuln_service.create_vuln(
        db, body.model_dump(), user.id, request.client.host if request.client else None
    )
    return ok(vuln, request)


@router.post("/import")
async def import_vulns(
    request: Request,
    db: DbSession,
    user: User = Depends(require_roles(Role.EDITOR, Role.ADMIN)),
    file: UploadFile | None = None,
    files: list[UploadFile] = File(default=[]),
    content: str | None = Form(default=None, description="CVE 内容文本（粘贴模式）"),
) -> dict:
    """批量导入 CVE（需要 editor 或 admin 角色）。

    支持单文件 / 批量文件上传 / 文本粘贴，单文件限制 10MB。
    支持格式：json、jsonl、yaml、markdown。导入管道自动判定格式、
    解析、去重合并（cve_id 已存在则仅补充空缺字段）。

    Args:
        request: 当前请求，用于记录来源 IP。
        db: 数据库会话。
        user: 断言具备 editor 或 admin 角色。
        file: 单文件（向后兼容）。
        files: 批量文件列表。
        content: 粘贴文本内容。

    Returns:
        dict: 标准响应体，data 为汇总导入结果。
    """
    from app.schemas.vuln import VulnImportResult

    MAX_SIZE = 10 * 1024 * 1024
    ip = request.client.host if request.client else None

    upload_files: list[UploadFile] = []
    if files:
        upload_files.extend(files)
    if file:
        upload_files.append(file)

    if upload_files:
        merged = VulnImportResult()
        for f in upload_files:
            file_content = await f.read()
            if len(file_content) > MAX_SIZE:
                merged.total += 1
                merged.failed.append({"name": f.filename, "error": "文件大小超过 10MB 限制"})
                continue
            sub = vuln_import_service.import_vulns(
                db,
                raw_content=file_content,
                filename=f.filename,
                user_id=user.id,
                ip=ip,
            )
            merged.total += sub.total
            merged.created += sub.created
            merged.updated += sub.updated
            merged.skipped += sub.skipped
            for item in sub.failed:
                merged.failed.append({"name": f.filename, **item} if "name" not in item else item)
        merged.success = merged.created + merged.updated
        return ok(merged.model_dump(), request)

    if content:
        result = vuln_import_service.import_vulns(
            db,
            raw_content=content,
            filename=None,
            user_id=user.id,
            ip=ip,
        )
        return ok(result.model_dump(), request)

    raise AppError(ErrorCode.REQUEST_INVALID, "请提供文件或粘贴内容")


@router.put("/{vuln_id}")
def update_vuln(
    request: Request,
    db: DbSession,
    vuln_id: int,
    body: VulnUpdate,
    user: User = Depends(require_roles(Role.EDITOR, Role.ADMIN)),
) -> dict:
    """更新 CVE 可编辑字段（需要 editor 或 admin 角色）。

    cve_id 不可修改。覆盖式更新各字段（传 None 表示清空），
    更新前记录审计日志。

    Args:
        request: 当前请求，用于记录来源 IP。
        db: 数据库会话。
        vuln_id: 目标漏洞 ID。
        body: 待更新字段（VulnUpdate）。
        user: 断言具备 editor 或 admin 角色。

    Returns:
        dict: 标准响应体，data 为更新后的漏洞详情。
    """
    vuln = vuln_service.update_vuln(
        db, vuln_id, body.model_dump(), user.id, request.client.host if request.client else None
    )
    return ok(vuln, request)


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
