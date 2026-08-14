"""标签服务层：CRUD 及 POC 关联统计。"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import AppError, ErrorCode, NotFoundError
from app.models.poc import PocTag, Tag
from app.schemas.tag import TagCreate, TagUpdate


def list_tags(
    db: Session,
    *,
    namespace: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[dict], int]:
    """分页查询标签列表，含每个标签关联的 POC 数量。"""
    query = select(Tag)
    if namespace:
        query = query.where(Tag.namespace == namespace)

    # 总数
    total = (
        db.scalar(
            select(func.count()).select_from(Tag).where(query.whereclause)
            if query.whereclause is not None
            else select(func.count()).select_from(Tag)
        )
        or 0
    )

    # 分页
    offset = (page - 1) * page_size
    tags = db.scalars(query.order_by(Tag.namespace, Tag.name).offset(offset).limit(page_size)).all()

    # 统计每个标签的 POC 数量
    result = []
    for tag in tags:
        poc_count = db.scalar(select(func.count()).select_from(PocTag).where(PocTag.tag_id == tag.id)) or 0
        result.append(_tag_to_dict(tag, poc_count))

    return result, total


def get_tag(db: Session, tag_id: int) -> dict:
    """获取标签详情（含 POC 数量）。"""
    tag = db.get(Tag, tag_id)
    if tag is None:
        raise NotFoundError("标签", str(tag_id))
    poc_count = db.scalar(select(func.count()).select_from(PocTag).where(PocTag.tag_id == tag.id)) or 0
    return _tag_to_dict(tag, poc_count)


def create_tag(db: Session, data: TagCreate) -> Tag:
    """创建标签（检查 (namespace, name) 唯一性）。"""
    existing = db.scalar(select(Tag).where(Tag.namespace == data.namespace, Tag.name == data.name))
    if existing:
        raise AppError(
            ErrorCode.CONFLICT,
            f"标签 '{data.namespace}:{data.name}' 已存在",
        )
    tag = Tag(
        namespace=data.namespace,
        name=data.name,
        color=data.color,
        description=data.description,
    )
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return tag


def update_tag(db: Session, tag_id: int, data: TagUpdate) -> Tag:
    """更新标签。"""
    tag = db.get(Tag, tag_id)
    if tag is None:
        raise NotFoundError("标签", str(tag_id))

    update_data = data.model_dump(exclude_unset=True)

    # 检查唯一性
    if "namespace" in update_data or "name" in update_data:
        new_namespace = update_data.get("namespace", tag.namespace)
        new_name = update_data.get("name", tag.name)
        if new_namespace != tag.namespace or new_name != tag.name:
            existing = db.scalar(
                select(Tag).where(
                    Tag.namespace == new_namespace,
                    Tag.name == new_name,
                    Tag.id != tag_id,
                )
            )
            if existing:
                raise AppError(ErrorCode.CONFLICT, f"标签 '{new_namespace}:{new_name}' 已存在")

    for field, value in update_data.items():
        if value is not None:
            setattr(tag, field, value)

    db.commit()
    db.refresh(tag)
    return tag


def delete_tag(db: Session, tag_id: int) -> None:
    """删除标签（级联删除 PocTag 关联）。"""
    tag = db.get(Tag, tag_id)
    if tag is None:
        raise NotFoundError("标签", str(tag_id))

    # 删除关联
    db.query(PocTag).where(PocTag.tag_id == tag_id).delete()
    db.delete(tag)
    db.commit()


def list_namespaces(db: Session) -> list[str]:
    """获取所有标签命名空间列表。"""
    rows = db.execute(select(Tag.namespace).distinct().order_by(Tag.namespace)).all()
    return [row[0] for row in rows]


def _tag_to_dict(tag: Tag, poc_count: int = 0) -> dict:
    """将 Tag ORM 对象转为字典。"""
    return {
        "id": tag.id,
        "namespace": tag.namespace,
        "name": tag.name,
        "color": tag.color,
        "description": tag.description,
        "poc_count": poc_count,
    }
