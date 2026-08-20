"""产品×版本命中查询 API 路由（开发方案 §5.9 核心查询）。

``GET /products/{slug}/pocs?version=2.3.15`` —— 给定产品与版本，返回命中 POC
列表；不带 version 时返回该产品关联的全量 POC。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field

from app.api.deps import CurrentUser, DbSession, require_roles
from app.core.security import Role
from app.models.user import User
from app.schemas.common import Page, ok
from app.services import product_service

router = APIRouter(prefix="/products", tags=["products"])


@router.get("")
def list_products(
    request: Request,
    db: DbSession,
    user: CurrentUser,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
    q: str | None = Query(default=None, description="按产品名/标识搜索"),
    vendor_q: str | None = Query(default=None, description="按厂商名筛选"),
) -> dict:
    """分页列出产品，供前端产品查询面板的自动补全使用。"""
    items, total = product_service.list_products(db, page=page, page_size=page_size, q=q, vendor_q=vendor_q)
    return ok({"items": items, "total": total}, request)


@router.get("/vendors")
def list_vendors(
    request: Request,
    db: DbSession,
    user: CurrentUser,
    q: str | None = Query(default=None, description="按厂商名搜索"),
) -> dict:
    """列出厂商，供前端自动补全使用。"""
    items = product_service.list_vendors(db, q=q)
    return ok({"items": items}, request)


@router.get("/{slug}/pocs")
def get_product_pocs(
    request: Request,
    db: DbSession,
    user: CurrentUser,
    slug: str,
    version: str | None = Query(default=None, description="目标版本号（向后兼容单版本模式）"),
    version_start: str | None = Query(default=None, description="版本范围：起始版本号"),
    version_start_op: str | None = Query(default=None, description="起始操作符: >= / > / <= / < / =="),
    version_end: str | None = Query(default=None, description="版本范围：截止版本号"),
    version_end_op: str | None = Query(default=None, description="截止操作符: >= / > / <= / < / =="),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
) -> dict:
    """按产品 slug + 版本范围查询命中 POC。

    版本匹配为应用层精确比较（VersionRange.overlaps），
    支持单版本（version）或版本范围（version_start + version_end + 操作符）两种模式。
    不带版本参数时返回产品关联的全量 POC（分页）。
    """
    items, total = product_service.get_pocs_for_product(
        db,
        slug,
        version=version,
        version_start=version_start,
        version_start_op=version_start_op,
        version_end=version_end,
        version_end_op=version_end_op,
        page=page,
        page_size=page_size,
    )
    result = Page.create(items, total, page, page_size)
    return ok(result.model_dump(), request)


class ProductCreate(BaseModel):
    """产品创建请求体。"""

    vendor_id: int = Field(..., description="所属厂商 ID")
    name: str = Field(..., min_length=1, max_length=128)
    slug: str = Field(..., min_length=1, max_length=128, pattern=r"^[a-z0-9\-]+$")
    category: str | None = Field(default=None, max_length=64)
    homepage: str | None = Field(default=None, max_length=255)
    description: str | None = None


@router.post("", status_code=200)
def create_product(
    request: Request,
    db: DbSession,
    body: ProductCreate,
    user: User = Depends(require_roles(Role.EDITOR, Role.ADMIN)),
) -> dict:
    """创建产品（编辑/管理员）。

    关联到厂商不影响 POC 查询接口；此处仅提供资产模型入场入口。
    """
    from sqlalchemy import select

    from app.core.exceptions import AppError, ErrorCode
    from app.models.poc import Product

    data = body.model_dump()
    if db.scalar(select(Product.id).where(Product.slug == data["slug"])):
        raise AppError(ErrorCode.CONFLICT, f"产品 slug '{data['slug']}' 已存在")
    product = Product(**data)
    db.add(product)
    db.commit()
    db.refresh(product)
    return ok(
        {
            "id": product.id,
            "slug": product.slug,
            "name": product.name,
            "vendor_id": product.vendor_id,
        },
        request,
    )
