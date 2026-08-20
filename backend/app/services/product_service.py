"""产品×版本命中查询服务（开发方案 §5.9 / §5.10）。

业务 API：``GET /products/{slug}/pocs?version=2.3.15``

查询流程：
1. 按 ``product.slug`` 精确匹配产品（§5.10），不存在抛 404；
2. 加载该产品（含其子组件）的 ``poc_affected`` 关联；
3. 带版本号时应用层逐条 ``VersionRange.matches()`` 精确筛选；
4. 同一 POC 多条区间命中去重（按 poc_id 聚合），保证列表唯一；
5. 排序 + 分页 + 复用 POC 列表项序列化（与 /pocs 口径一致）。
"""

from __future__ import annotations

import datetime as dt
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import AppError, ErrorCode, NotFoundError
from app.core.versioning import Version, VersionRange, normalize_version
from app.models.poc import Component, Poc, PocAffected, PocCategory, PocTag, PocVuln, Product, Vendor
from app.services.poc_service import _build_poc_list_item

__all__ = ["get_pocs_for_product", "list_products", "list_vendors"]


def get_product(db: Session, slug: str) -> Product | None:
    """按 slug 精确匹配产品。"""
    return db.scalar(select(Product).where(Product.slug == slug))


def _get_product_or_404(db: Session, slug: str) -> Product:
    product = get_product(db, slug)
    if product is None:
        raise NotFoundError("产品", slug)
    return product


def _affected_stmt(product: Product, component_ids: list[int]):
    """产品维度（含子组件）的 poc_affected 查询，预加载 POC 及其常用关联。"""
    filters = [PocAffected.product_id == product.id]
    if component_ids:
        filters.append(PocAffected.component_id.in_(component_ids))
    return (
        select(PocAffected)
        .options(
            selectinload(PocAffected.poc).selectinload(Poc.tags).selectinload(PocTag.tag),
            selectinload(PocAffected.poc).selectinload(Poc.vulns).selectinload(PocVuln.vuln),
            selectinload(PocAffected.poc).selectinload(Poc.categories).selectinload(PocCategory.category),
            selectinload(PocAffected.poc).selectinload(Poc.affected),
        )
        .where(or_(*filters))
    )


def _poc_matches(affected: PocAffected, version: Version) -> bool:
    """单个影响范围的版本命中判定（单版本匹配）。"""
    if affected.version_start is None and affected.version_end is None and not affected.version_expression:
        return True
    return VersionRange(
        affected.version_start,
        affected.version_start_type,
        affected.version_end,
        affected.version_end_type,
        affected.version_expression,
    ).matches(version)


def _poc_range_overlaps(affected: PocAffected, query_range: VersionRange) -> bool:
    """单个影响范围与查询区间是否有重叠（版本范围搜索）。"""
    if affected.version_start is None and affected.version_end is None and not affected.version_expression:
        return True
    affected_range = VersionRange(
        affected.version_start,
        affected.version_start_type,
        affected.version_end,
        affected.version_end_type,
        affected.version_expression,
    )
    return affected_range.overlaps(query_range)


def _parse_version(version: str) -> Version:
    """解析查询参数版本号，非法格式返回 400。"""
    try:
        return Version.from_normalized(normalize_version(version.strip()))
    except ValueError:
        raise AppError(ErrorCode.REQUEST_INVALID, f"版本号格式非法: {version}") from None


def _build_query_range(
    version_start: str | None,
    version_start_op: str | None,
    version_end: str | None,
    version_end_op: str | None,
) -> VersionRange | None:
    """从查询参数构建搜索区间；全为空时返回 None（无版本筛选）。"""
    if not version_start and not version_end:
        return None
    # 前端操作符映射到后端语义键
    return VersionRange(version_start, version_start_op, version_end, version_end_op)


def get_pocs_for_product(
    db: Session,
    slug: str,
    version: str | None = None,
    *,
    page: int = 1,
    page_size: int = 20,
    version_start: str | None = None,
    version_start_op: str | None = None,
    version_end: str | None = None,
    version_end_op: str | None = None,
) -> tuple[list[dict], int]:
    """查询指定产品的命中 POC 列表。

    Args:
        db: 数据库会话。
        slug: 产品标识（精确匹配）。
        version: 目标版本号（形如 ``2.3.15``）。向后兼容的单版本模式。
        page / page_size: 分页参数。
        version_start / version_start_op / version_end / version_end_op:
            版本范围搜索参数（优先级高于单版本参数）。

    Returns:
        (items, total)：items 为 POC 列表项字典（同 /pocs 列表口径），
        total 为命中 POC 总数（去重后）。
    """
    product = _get_product_or_404(db, slug)
    component_ids = list(db.scalars(select(Component.id).where(Component.product_id == product.id)).all())

    # 确定匹配模式：范围优先，单版本次之，全量兜底
    query_range = _build_query_range(version_start, version_start_op, version_end, version_end_op)
    target = _parse_version(version) if version and not query_range else None

    # 去重：同一 POC 命中多条区间只算一次（dict 以 poc_id 为键天然去重）。
    matched: dict[int, Poc] = {}
    for row in db.scalars(_affected_stmt(product, component_ids)).all():
        poc = row.poc
        if poc is None:
            continue
        if query_range:
            if _poc_range_overlaps(row, query_range):
                matched.setdefault(poc.id, poc)
        elif target:
            if _poc_matches(row, target):
                matched.setdefault(poc.id, poc)
        else:
            matched.setdefault(poc.id, poc)

    pocs = list(matched.values())
    pocs.sort(key=lambda p: p.created_at or dt.datetime(1970, 1, 1), reverse=True)

    total = len(pocs)
    offset = (page - 1) * page_size
    items = [_build_poc_list_item(p) for p in pocs[offset : offset + page_size]]
    return items, total


def list_products(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 20,
    q: str | None = None,
    vendor_q: str | None = None,
) -> tuple[list[dict], int]:
    """分页列出产品（slug 精确匹配 + name LIKE 模糊，§5.10）。"""
    query = select(Product)
    if q:
        like = f"%{q}%"
        query = query.where(or_(Product.slug.ilike(like), Product.name.ilike(like)))
    if vendor_q:
        like = f"%{vendor_q}%"
        query = query.join(Product.vendor).where(Vendor.name.ilike(like))
    total: int = 0
    if query.whereclause is not None:
        total = db.scalar(select(func.count()).select_from(Product).where(*(query.whereclause,))) or 0
    else:
        total = db.scalar(select(func.count()).select_from(Product)) or 0

    offset = (page - 1) * page_size
    rows = db.scalars(query.order_by(Product.name).offset(offset).limit(page_size)).all()

    items: list[dict[str, Any]] = []
    for product in rows:
        poc_total = (
            db.scalar(
                select(func.count(func.distinct(PocAffected.poc_id))).where(
                    PocAffected.product_id == product.id
                )
            )
            or 0
        )
        items.append(
            {
                "id": product.id,
                "slug": product.slug,
                "name": product.name,
                "vendor": product.vendor.name if product.vendor else None,
                "category": product.category,
                "homepage": product.homepage,
                "description": product.description,
                "poc_count": poc_total,
            }
        )
    return items, total


def list_vendors(
    db: Session,
    *,
    q: str | None = None,
) -> list[dict]:
    """列出厂商，按名称搜索，供前端自动补全使用。"""
    query = select(Vendor)
    if q:
        like = f"%{q}%"
        query = query.where(Vendor.name.ilike(like))
    rows = db.scalars(query.order_by(Vendor.name)).all()
    return [
        {
            "slug": v.slug,
            "name": v.name,
            "product_count": len(v.products),
        }
        for v in rows
    ]
