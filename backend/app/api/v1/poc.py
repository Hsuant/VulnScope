"""POC API 路由：CRUD、搜索、版本管理、克隆、状态流转。

所有接口均需认证，写操作需要 editor 或 admin 角色。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field

from app.api.deps import CurrentUser, DbSession, require_roles
from app.core.security import Role
from app.core.timeutil import iso_utc
from app.models.user import User
from app.schemas.common import Page, ok
from app.schemas.poc import (
    PocCloneRequest,
    PocCreate,
    PocStatusChange,
    PocUpdate,
)
from app.services import poc_service

router = APIRouter(prefix="/pocs", tags=["pocs"])


# ── 查询参数依赖 ─────────────────────────────────────────────────────────


class PocQueryParams:
    """POC 列表查询参数（FastAPI 依赖注入形式）。"""

    def __init__(
        self,
        page: int = Query(default=1, ge=1, description="页码"),
        page_size: int = Query(default=20, ge=1, le=100, description="每页条数"),
        sort_by: str = Query(default="created_at", description="排序字段"),
        sort_order: str = Query(default="desc", description="排序方向: asc/desc"),
        severity: str | None = Query(default=None, description="按严重级别筛选"),
        status: str | None = Query(default=None, description="按状态筛选"),
        source: str | None = Query(default=None, description="按来源筛选"),
        format: str | None = Query(default=None, description="按格式筛选"),
        author: str | None = Query(default=None, description="按作者筛选"),
        tag_ids: str | None = Query(default=None, description="标签 ID 列表（逗号分隔，OR 逻辑）"),
        tag_ids_all: str | None = Query(
            default=None, description="标签 ID 列表（逗号分隔，AND 逻辑，须同时满足所有标签）"
        ),
        cve: str | None = Query(default=None, description="CVE 编号搜索"),
        category_id: int | None = Query(default=None, description="分类 ID"),
        created_at_from: str | None = Query(default=None, description="创建起始时间"),
        created_at_to: str | None = Query(default=None, description="创建截止时间"),
        q: str | None = Query(default=None, description="关键字搜索（名称/标题/描述）"),
        search_content: bool = Query(default=False, description="搜索范围扩展到 POC 正文 content"),
    ):
        self.page = page
        self.page_size = page_size
        self.sort_by = sort_by
        self.sort_order = sort_order
        self.severity = severity
        self.status = status
        self.source = source
        self.format = format
        self.author = author
        self.tag_ids = [int(x.strip()) for x in tag_ids.split(",") if x.strip()] if tag_ids else None
        self.tag_ids_all = (
            [int(x.strip()) for x in tag_ids_all.split(",") if x.strip()] if tag_ids_all else None
        )
        self.cve = cve
        self.category_id = category_id
        self.created_at_from = created_at_from
        self.created_at_to = created_at_to
        self.q = q
        self.search_content = search_content


@router.get("")
def list_pocs(
    request: Request,
    db: DbSession,
    user: CurrentUser,
    params: PocQueryParams = Depends(),
) -> dict:
    """分页查询 POC 列表。

    支持多条件组合过滤、关键字搜索（名称/标题/描述）、排序、分页。
    """
    items, total = poc_service.list_pocs(
        db,
        page=params.page,
        page_size=params.page_size,
        sort_by=params.sort_by,
        sort_order=params.sort_order,
        severity=params.severity,
        status=params.status,
        source=params.source,
        format=params.format,
        author=params.author,
        tag_ids=params.tag_ids,
        tag_ids_all=params.tag_ids_all,
        cve=params.cve,
        category_id=params.category_id,
        created_at_from=params.created_at_from,
        created_at_to=params.created_at_to,
        q=params.q,
        search_content=params.search_content,
    )

    # 转换为列表项格式
    list_items = [poc_service._build_poc_list_item(p) for p in items]
    page = Page.create(list_items, total, params.page, params.page_size)
    return ok(page.model_dump(), request)


# ── 关键字搜索 ──────────────────────────────────────────────────────────


@router.get("/search")
def search_pocs(
    request: Request,
    db: DbSession,
    user: CurrentUser,
    q: str = Query(..., min_length=1, max_length=200, description="搜索关键词"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search_content: bool = Query(default=False, description="搜索范围扩展到 POC 正文 content"),
) -> dict:
    """关键字搜索 POC（名称/标题/描述/CVE，search_content 扩展正文）。"""
    items, total = poc_service.list_pocs(
        db,
        q=q,
        page=page,
        page_size=page_size,
        search_content=search_content,
    )
    list_items = [poc_service._build_poc_list_item(p) for p in items]
    result = Page.create(list_items, total, page, page_size)
    return ok(result.model_dump(), request)


# ── 创建 ────────────────────────────────────────────────────────────────


@router.post("", status_code=200)
def create_poc(
    request: Request,
    db: DbSession,
    body: PocCreate,
    user: User = Depends(require_roles(Role.EDITOR, Role.ADMIN)),
) -> dict:
    """创建 POC（需要 editor 或 admin 角色）。

    自动计算 content_hash 去重，创建首条版本快照，发布领域事件。
    """
    poc = poc_service.create_poc(db, body, user.id, request.client.host if request.client else None)
    return ok(poc_service._build_poc_detail(poc), request)


# ── 详情 ────────────────────────────────────────────────────────────────


@router.get("/{poc_id}")
def get_poc(
    request: Request,
    db: DbSession,
    user: CurrentUser,
    poc_id: int,
) -> dict:
    """获取 POC 详情（含 content 全文、标签、CVE、分类信息）。"""
    poc = poc_service.get_poc(db, poc_id)
    return ok(poc_service._build_poc_detail(poc), request)


# ── 更新 ────────────────────────────────────────────────────────────────


@router.put("/{poc_id}")
def update_poc(
    request: Request,
    db: DbSession,
    poc_id: int,
    body: PocUpdate,
    user: User = Depends(require_roles(Role.EDITOR, Role.ADMIN)),
) -> dict:
    """更新 POC（需要 editor 或 admin 角色）。

    支持部分更新：仅传入需要修改的字段。
    内容变更时自动创建版本快照，并检查 content_hash 去重。
    """
    poc = poc_service.update_poc(
        db,
        poc_id,
        body,
        user.id,
        request.client.host if request.client else None,
    )
    return ok(poc_service._build_poc_detail(poc), request)


# ── 删除 ────────────────────────────────────────────────────────────────


@router.delete("/{poc_id}")
def delete_poc(
    request: Request,
    db: DbSession,
    poc_id: int,
    user: User = Depends(require_roles(Role.EDITOR, Role.ADMIN)),
) -> dict:
    """删除 POC（需要 editor 或 admin 角色）。

    硬删除，级联清理关联数据（标签/CVE/分类/版本历史），操作前记录审计日志。
    """
    poc_service.delete_poc(db, poc_id, user.id, request.client.host if request.client else None)
    return ok({"deleted": True}, request)


# ── 状态流转 ────────────────────────────────────────────────────────────


@router.patch("/{poc_id}/status")
def change_poc_status(
    request: Request,
    db: DbSession,
    poc_id: int,
    body: PocStatusChange,
    user: User = Depends(require_roles(Role.EDITOR, Role.ADMIN)),
) -> dict:
    """变更 POC 状态（需要 editor 或 admin 角色）。

    合法的状态流转：
    - draft → active / disabled
    - active → disabled / archived
    - disabled → active / archived
    - archived → active
    """
    poc = poc_service.change_poc_status(
        db,
        poc_id,
        body,
        user.id,
        request.client.host if request.client else None,
    )
    return ok(poc_service._build_poc_detail(poc), request)


# ── 克隆 ────────────────────────────────────────────────────────────────


@router.post("/{poc_id}/clone")
def clone_poc(
    request: Request,
    db: DbSession,
    poc_id: int,
    body: PocCloneRequest,
    user: User = Depends(require_roles(Role.EDITOR, Role.ADMIN)),
) -> dict:
    """克隆 POC（需要 editor 或 admin 角色）。

    复制原 POC 的内容、标签、CVE 关联、分类关联，使用新名称创建独立 POC。
    新 POC 状态恒为 draft。
    """
    poc = poc_service.clone_poc(
        db,
        poc_id,
        body,
        user.id,
        request.client.host if request.client else None,
    )
    return ok(poc_service._build_poc_detail(poc), request)


# ── 版本历史 ────────────────────────────────────────────────────────────


@router.get("/{poc_id}/versions")
def get_poc_versions(
    request: Request,
    db: DbSession,
    user: CurrentUser,
    poc_id: int,
) -> dict:
    """获取 POC 版本历史列表。"""
    versions = poc_service.get_poc_versions(db, poc_id)
    items = [
        {
            "id": v.id,
            "version_seq": v.version_seq,
            "content_hash": v.content_hash,
            "changed_by": v.changed_by,
            "changed_at": iso_utc(v.changed_at),
        }
        for v in versions
    ]
    return ok(items, request)


# ── 溯源记录 ────────────────────────────────────────────────────────────


@router.get("/{poc_id}/source-records")
def get_poc_source_records(
    request: Request,
    db: DbSession,
    user: CurrentUser,
    poc_id: int,
) -> dict:
    """获取 POC 来源溯源记录。"""
    from sqlalchemy import select

    from app.models.poc import PocSourceRecord

    poc = poc_service.get_poc(db, poc_id)
    records = db.scalars(
        select(PocSourceRecord)
        .where(PocSourceRecord.poc_id == poc.id)
        .order_by(PocSourceRecord.fetched_at.desc())
    ).all()

    items = [
        {
            "id": r.id,
            "source_type": r.source_type,
            "batch_id": r.batch_id,
            "source_url": r.source_url,
            "ref_id": r.ref_id,
            "fetched_at": iso_utc(r.fetched_at),
            "extra_meta": r.extra_meta,
        }
        for r in records
    ]
    return ok(items, request)


# ── 参考链接验证 ──────────────────────────────────────────────────────────


class VerifyUrlRequest(BaseModel):
    url: str = Field(..., max_length=512, description="待验证的 URL")


@router.post("/verify-url", status_code=200)
def verify_url(
    request: Request,
    body: VerifyUrlRequest,
    user: CurrentUser,
) -> dict:
    """验证参考链接的可访问性。

    发送 HEAD 请求检查 URL 是否可达，返回状态码和耗时。
    """
    import httpx

    url = body.url.strip()
    if not url.startswith(("http://", "https://")):
        return ok({"url": url, "reachable": False, "status_code": 0, "error": "仅支持 http/https 协议"})

    try:
        with httpx.Client(timeout=10.0, follow_redirects=True) as client:
            resp = client.head(url)
            return ok(
                {
                    "url": url,
                    "reachable": resp.is_success or resp.is_redirect,
                    "status_code": resp.status_code,
                    "error": None,
                }
            )
    except httpx.TimeoutException:
        return ok({"url": url, "reachable": False, "status_code": 0, "error": "连接超时"})
    except httpx.ConnectError:
        return ok({"url": url, "reachable": False, "status_code": 0, "error": "无法连接"})
    except Exception as e:
        return ok({"url": url, "reachable": False, "status_code": 0, "error": str(e)})
