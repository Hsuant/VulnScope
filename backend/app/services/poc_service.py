"""POC 服务层：CRUD、搜索、版本管理、克隆、状态流转。

提供完整的事务边界，所有写操作发布领域事件并写入审计日志。
"""

from __future__ import annotations

import datetime as dt
import hashlib
import uuid
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.events import DomainEvent, event_bus
from app.core.exceptions import AppError, ErrorCode, NotFoundError
from app.models.poc import (
    AuditLog,
    Category,
    Poc,
    PocAffected,
    PocCategory,
    PocTag,
    PocVersion,
    PocVuln,
    Tag,
    Vuln,
)
from app.schemas.poc import (
    SEVERITY_ORDER,
    STATUS_TRANSITIONS,
    PocCloneRequest,
    PocCreate,
    PocStatusChange,
    PocUpdate,
)

# ── 工具函数 ────────────────────────────────────────────────────────────


def _normalize_content(content: str) -> str:
    """归一化 POC 内容：统一换行符、去除行尾空白、末尾单换行。

    归一化后的内容用于计算 content_hash，保证去重一致性。
    """
    content = content.strip()
    content = content.replace("\r\n", "\n").replace("\r", "\n")
    content = "\n".join(line.rstrip() for line in content.split("\n"))
    content = content.rstrip("\n") + "\n"
    return content


def _compute_content_hash(content: str) -> str:
    """计算归一化后内容的 SHA-256 摘要。"""
    normalized = _normalize_content(content)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _create_audit_log(
    db: Session,
    user_id: int | None,
    action: str,
    resource_type: str,
    resource_id: str | None,
    detail: dict[str, Any] | None = None,
    ip: str | None = None,
) -> None:
    """写入审计日志。"""
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


def _publish_event(event_type: str, aggregate_id: str | None, payload: dict[str, Any] | None = None) -> None:
    """发布领域事件（异步派发，不阻塞当前事务）。"""
    event = DomainEvent(event_type=event_type, aggregate_id=aggregate_id, payload=payload)
    event_bus.publish(event)


def _get_poc_or_404(db: Session, poc_id: int) -> Poc:
    """按 ID 查询 POC，不存在时抛 NotFoundError。"""
    poc = db.get(Poc, poc_id)
    if poc is None:
        raise NotFoundError("POC", str(poc_id))
    return poc


def _load_poc_relations(stmt: Any) -> Any:
    """为查询添加常用的 selectinload，避免 N+1 问题。"""
    return stmt.options(
        selectinload(Poc.tags).selectinload(PocTag.tag),
        selectinload(Poc.vulns).selectinload(PocVuln.vuln),
        selectinload(Poc.categories).selectinload(PocCategory.category),
        selectinload(Poc.affected),
    )


def _extract_tags(poc: Poc) -> list[dict]:
    """从 POC 对象中提取标签简要信息。"""
    return [
        {"id": pt.tag.id, "namespace": pt.tag.namespace, "name": pt.tag.name, "color": pt.tag.color}
        for pt in poc.tags
        if pt.tag
    ]


def _extract_cve_ids(poc: Poc) -> list[str]:
    """从 POC 对象中提取关联 CVE 编号列表。"""
    return [pv.vuln.cve_id for pv in poc.vulns if pv.vuln]


def _extract_categories(poc: Poc) -> list[dict]:
    """从 POC 对象中提取分类简要信息。"""
    return [
        {"id": pc.category.id, "name": pc.category.name, "slug": pc.category.slug}
        for pc in poc.categories
        if pc.category
    ]


def _extract_affected_versions(poc: Poc) -> list[dict]:
    """从 POC 对象中提取版本影响范围。"""
    return [
        {
            "version_start": a.version_start,
            "version_start_type": a.version_start_type,
            "version_end": a.version_end,
            "version_end_type": a.version_end_type,
        }
        for a in poc.affected
    ]


# ── 核心 CRUD ──────────────────────────────────────────────────────────


def create_poc(db: Session, data: PocCreate, user_id: int | None = None, ip: str | None = None) -> Poc:
    """创建 POC。

    步骤：
    1. 校验 content_hash 去重
    2. 校验 (name, source) 唯一性
    3. 创建 POC 记录
    4. 关联 CVE/Tag/Category
    5. 创建首条版本快照
    6. 发布事件 + 审计日志
    """
    # 计算内容哈希
    content_hash = _compute_content_hash(data.content)

    # 去重检查：相同 content_hash 的 POC 已存在
    existing = db.scalar(select(Poc).where(Poc.content_hash == content_hash))
    if existing:
        raise AppError(
            ErrorCode.POC_DUPLICATE,
            f"内容重复: 已存在同名 POC '{existing.name}' (id={existing.id})",
            detail={"existing_id": existing.id, "existing_name": existing.name},
        )

    # 唯一性检查：(name, source) 联合唯一
    existing_name = db.scalar(select(Poc).where(Poc.name == data.name, Poc.source == data.source))
    if existing_name:
        raise AppError(
            ErrorCode.CONFLICT,
            f"POC 名称 '{data.name}' 在来源 '{data.source}' 下已存在",
        )

    # 创建 POC
    poc_uuid = str(uuid.uuid4())
    poc = Poc(
        uuid=poc_uuid,
        name=data.name,
        title=data.title,
        description=data.description,
        severity=data.severity,
        format=data.format,
        language=data.language,
        content=_normalize_content(data.content),
        content_hash=content_hash,
        author=data.author,
        source=data.source,
        status=data.status,
        version=1,
        extra_meta=data.extra_meta or None,
        created_by=user_id,
        updated_by=user_id,
    )
    db.add(poc)
    db.flush()  # 获取 poc.id

    # 关联 CVE
    _sync_cve_ids(db, poc, data.cve_ids)

    # 存储 CNVD 编号到 extra_meta
    if data.cnvd_ids:
        meta = dict(poc.extra_meta or {})
        meta["cnvd_ids"] = data.cnvd_ids
        poc.extra_meta = meta

    # 存储参考链接到 extra_meta
    if data.references:
        meta = dict(poc.extra_meta or {})
        meta["references"] = [r.model_dump() for r in data.references]
        poc.extra_meta = meta

    # 存储资产探测 FOFA 语法到 extra_meta
    if data.fofa_syntax:
        meta = dict(poc.extra_meta or {})
        meta["fofa_syntax"] = data.fofa_syntax
        poc.extra_meta = meta

    # 存储资产探测 Shodan 语法到 extra_meta
    if data.shodan_syntax:
        meta = dict(poc.extra_meta or {})
        meta["shodan_syntax"] = data.shodan_syntax
        poc.extra_meta = meta

    # 关联标签
    _sync_tag_ids(db, poc, data.tag_ids)

    # 关联分类
    _sync_category_ids(db, poc, data.category_ids)

    # 关联版本影响范围
    _sync_affected_versions(db, poc, [v.model_dump() for v in data.affected_versions])

    # 创建首条版本快照
    _create_version_snapshot(db, poc, user_id)

    db.flush()
    db.commit()

    # 发布事件 + 审计日志
    _publish_event("poc.created", str(poc.id), {"name": poc.name, "severity": poc.severity})
    _create_audit_log(db, user_id, "poc.created", "poc", str(poc.id), {"poc_name": poc.name}, ip)
    db.commit()

    # 重新加载关联数据
    return _reload_poc(db, poc.id)


def get_poc(db: Session, poc_id: int) -> Poc:
    """获取 POC 详情（含所有关联数据）。"""
    stmt = _load_poc_relations(select(Poc).where(Poc.id == poc_id))
    poc = db.scalar(stmt)
    if poc is None:
        raise NotFoundError("POC", str(poc_id))
    return poc


def update_poc(
    db: Session, poc_id: int, data: PocUpdate, user_id: int | None = None, ip: str | None = None
) -> Poc:
    """更新 POC。

    支持部分更新：仅更新传入的字段。
    内容变更时自动创建版本快照，并检查 content_hash 去重。
    """
    poc = _get_poc_or_404(db, poc_id)
    before_status = poc.status

    # 收集变更摘要（用于审计日志）
    changes: dict[str, Any] = {"before": {}, "after": {}}

    # 逐字段更新
    update_fields = data.model_dump(exclude_unset=True)

    # 处理内容变更（特殊逻辑：需要创建版本快照 + 检查去重）
    content_changed = False
    if "content" in update_fields:
        new_content = update_fields.pop("content")
        new_hash = _compute_content_hash(new_content)

        if new_hash != poc.content_hash:
            # 检查新内容是否与其他 POC 重复
            dup = db.scalar(select(Poc).where(Poc.content_hash == new_hash, Poc.id != poc_id))
            if dup:
                raise AppError(
                    ErrorCode.POC_DUPLICATE,
                    f"更新后内容与已有 POC '{dup.name}' 重复",
                    detail={"existing_id": dup.id, "existing_name": dup.name},
                )
            # 保存当前内容为版本快照
            _create_version_snapshot(db, poc, user_id)
            # 更新内容
            poc.content = _normalize_content(new_content)
            poc.content_hash = new_hash
            content_changed = True
            changes["before"]["content"] = True
            changes["after"]["content"] = True

    # 处理名称变更（检查唯一性）
    if "name" in update_fields and update_fields["name"] != poc.name:
        existing_name = db.scalar(
            select(Poc).where(Poc.name == update_fields["name"], Poc.source == poc.source, Poc.id != poc_id)
        )
        if existing_name:
            raise AppError(
                ErrorCode.CONFLICT, f"POC 名称 '{update_fields['name']}' 在来源 '{poc.source}' 下已存在"
            )
        changes["before"]["name"] = poc.name
        changes["after"]["name"] = update_fields["name"]

    # 处理状态变更（特殊逻辑：校验流转规则）
    if "status" in update_fields and update_fields["status"] != poc.status:
        new_status = update_fields["status"]
        allowed = STATUS_TRANSITIONS.get(poc.status, set())
        if new_status not in allowed:
            raise AppError(
                ErrorCode.POC_INVALID_STATUS_TRANSITION,
                f"不允许从 '{poc.status}' 转换到 '{new_status}'，允许目标: {', '.join(sorted(allowed)) if allowed else '无'}",
            )
        changes["before"]["status"] = poc.status
        changes["after"]["status"] = new_status

    # 处理关联数据（CVE/Tags/Categories）
    if "cve_ids" in update_fields:
        _sync_cve_ids(db, poc, update_fields.pop("cve_ids"))
        changes["after"]["cve_ids"] = True

    if "cnvd_ids" in update_fields:
        cnvd_ids = update_fields.pop("cnvd_ids")
        meta = dict(poc.extra_meta or {})
        if cnvd_ids:
            meta["cnvd_ids"] = cnvd_ids
        else:
            meta.pop("cnvd_ids", None)
        poc.extra_meta = meta
        changes["after"]["cnvd_ids"] = True

    if "references" in update_fields:
        refs = update_fields.pop("references")
        meta = dict(poc.extra_meta or {})
        if refs:
            meta["references"] = refs
        else:
            meta.pop("references", None)
        poc.extra_meta = meta
        changes["after"]["references"] = True

    if "fofa_syntax" in update_fields:
        fofa = update_fields.pop("fofa_syntax")
        meta = dict(poc.extra_meta or {})
        if fofa:
            meta["fofa_syntax"] = fofa
        else:
            meta.pop("fofa_syntax", None)
        poc.extra_meta = meta
        changes["after"]["fofa_syntax"] = True

    if "shodan_syntax" in update_fields:
        shodan = update_fields.pop("shodan_syntax")
        meta = dict(poc.extra_meta or {})
        if shodan:
            meta["shodan_syntax"] = shodan
        else:
            meta.pop("shodan_syntax", None)
        poc.extra_meta = meta
        changes["after"]["shodan_syntax"] = True

    if "tag_ids" in update_fields:
        _sync_tag_ids(db, poc, update_fields.pop("tag_ids"))
        changes["after"]["tag_ids"] = True

    if "category_ids" in update_fields:
        _sync_category_ids(db, poc, update_fields.pop("category_ids"))
        changes["after"]["category_ids"] = True

    if "affected_versions" in update_fields:
        _sync_affected_versions(db, poc, update_fields.pop("affected_versions"))
        changes["after"]["affected_versions"] = True

    # 合并扩展元数据：前端传入的 extra_meta（主要是 builder 状态等自由字段）叠加到
    # 当前 poc.extra_meta 之上，但已被独立字段管理的键（references/cnvd_ids/fofa_syntax）
    # 以服务端刚写入的值为准，避免被前端携带的旧值覆盖。
    if "extra_meta" in update_fields:
        incoming = update_fields.pop("extra_meta") or {}
        meta = dict(poc.extra_meta or {})
        managed = {"references", "cnvd_ids", "fofa_syntax", "shodan_syntax"}
        for k, v in incoming.items():
            if k in managed:
                continue
            meta[k] = v
        poc.extra_meta = meta or None
        changes["after"]["extra_meta"] = True

    # 更新普通字段
    for field, value in update_fields.items():
        if hasattr(poc, field):
            if value is not None:
                changes["before"].get(field, poc.__dict__.get(field))
                changes["after"][field] = value
            setattr(poc, field, value)

    poc.version += 1
    poc.updated_by = user_id
    db.flush()
    db.commit()

    # 发布事件
    event_type = "poc.updated"
    if content_changed:
        event_type = "poc.version_created"
    if "status" in update_fields and update_fields.get("status") != before_status:
        event_type = "poc.status_changed"

    _publish_event(
        event_type, str(poc.id), {"name": poc.name, "changes": list(changes.get("after", {}).keys())}
    )
    _create_audit_log(
        db,
        user_id,
        event_type,
        "poc",
        str(poc.id),
        {"poc_name": poc.name, **changes},
        ip,
    )
    db.commit()

    return _reload_poc(db, poc.id)


def delete_poc(db: Session, poc_id: int, user_id: int | None = None, ip: str | None = None) -> None:
    """删除 POC（硬删除，级联清理关联数据）。

    删除前记录审计日志，删除后发布事件。
    """
    poc = _get_poc_or_404(db, poc_id)
    poc_name = poc.name

    # 记录审计日志（删除前，因为删除后数据不可查）
    _create_audit_log(
        db,
        user_id,
        "poc.deleted",
        "poc",
        str(poc_id),
        {"poc_name": poc_name, "severity": poc.severity, "source": poc.source},
        ip,
    )

    # 发布事件
    _publish_event("poc.deleted", str(poc_id), {"name": poc_name})

    # 执行删除（级联删除关联数据）
    db.delete(poc)
    db.commit()


# ── 列表查询 ───────────────────────────────────────────────────────────


def list_pocs(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 20,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    severity: str | None = None,
    status: str | None = None,
    source: str | None = None,
    format: str | None = None,
    author: str | None = None,
    tag_ids: list[int] | None = None,
    cve: str | None = None,
    category_id: int | None = None,
    created_at_from: str | None = None,
    created_at_to: str | None = None,
    q: str | None = None,
) -> tuple[list[Poc], int]:
    """分页查询 POC 列表。

    支持多条件组合过滤、关键字搜索、排序、分页。
    返回 (items, total) 二元组。
    """
    # 基础查询
    base_query = select(Poc)

    # 关键字搜索（名称/标题/描述）
    if q:
        like_pattern = f"%{q}%"
        base_query = base_query.where(
            or_(
                Poc.name.ilike(like_pattern),
                Poc.title.ilike(like_pattern),
                Poc.description.ilike(like_pattern),
            )
        )

    # 精确过滤
    if severity:
        base_query = base_query.where(Poc.severity == severity)
    if status:
        base_query = base_query.where(Poc.status == status)
    if source:
        base_query = base_query.where(Poc.source == source)
    if format:
        base_query = base_query.where(Poc.format == format)
    if author:
        base_query = base_query.where(Poc.author.ilike(f"%{author}%"))

    # 标签过滤（通过 PocTag 子查询）
    if tag_ids:
        base_query = base_query.where(Poc.id.in_(select(PocTag.poc_id).where(PocTag.tag_id.in_(tag_ids))))

    # CVE 过滤（通过 PocVuln + Vuln 子查询）
    if cve:
        base_query = base_query.where(
            Poc.id.in_(
                select(PocVuln.poc_id)
                .join(Vuln, PocVuln.vuln_id == Vuln.id)
                .where(Vuln.cve_id.ilike(f"%{cve}%"))
            )
        )

    # 分类过滤
    if category_id:
        base_query = base_query.where(
            Poc.id.in_(select(PocCategory.poc_id).where(PocCategory.category_id == category_id))
        )

    # 时间范围过滤
    if created_at_from:
        try:
            dt_from = dt.datetime.fromisoformat(created_at_from)
            base_query = base_query.where(Poc.created_at >= dt_from)
        except ValueError:
            pass
    if created_at_to:
        try:
            dt_to = dt.datetime.fromisoformat(created_at_to)
            base_query = base_query.where(Poc.created_at <= dt_to)
        except ValueError:
            pass

    # 总数查询
    count_query = (
        select(func.count()).select_from(Poc).where(base_query.whereclause)  # 复用过滤条件
        if base_query.whereclause is not None
        else select(func.count()).select_from(Poc)
    )
    total = db.scalar(count_query) or 0

    # 排序
    valid_sort_fields = {
        "created_at": Poc.created_at,
        "updated_at": Poc.updated_at,
        "name": Poc.name,
        "severity": Poc.severity,
        "status": Poc.status,
        "source": Poc.source,
    }
    sort_column: Any = valid_sort_fields.get(sort_by, Poc.created_at)

    if sort_by == "severity":
        # 严重级别按自定义权重排序，而非字母序
        from sqlalchemy import case

        sort_column = case(
            *[(Poc.severity == k, v) for k, v in SEVERITY_ORDER.items()],
            else_=0,
        )

    order = sort_column.asc() if sort_order == "asc" else sort_column.desc()
    base_query = base_query.order_by(order)

    # 分页
    offset = (page - 1) * page_size
    base_query = base_query.offset(offset).limit(page_size)

    # 加载关联数据
    query = _load_poc_relations(base_query)
    items = list(db.scalars(query).all())

    return items, total


# ── 状态流转 ───────────────────────────────────────────────────────────


def change_poc_status(
    db: Session, poc_id: int, data: PocStatusChange, user_id: int | None = None, ip: str | None = None
) -> Poc:
    """变更 POC 状态，校验流转规则合法性。"""
    poc = _get_poc_or_404(db, poc_id)
    new_status = data.status

    if new_status == poc.status:
        return _reload_poc(db, poc.id)

    allowed = STATUS_TRANSITIONS.get(poc.status, set())
    if new_status not in allowed:
        raise AppError(
            ErrorCode.POC_INVALID_STATUS_TRANSITION,
            f"不允许从 '{poc.status}' 转换到 '{new_status}'",
        )

    old_status = poc.status
    poc.status = new_status
    poc.version += 1
    poc.updated_by = user_id
    db.flush()

    # 事件 + 审计
    _publish_event(
        "poc.status_changed", str(poc.id), {"name": poc.name, "from": old_status, "to": new_status}
    )
    _create_audit_log(
        db,
        user_id,
        "poc.status_changed",
        "poc",
        str(poc.id),
        {"poc_name": poc.name, "before": {"status": old_status}, "after": {"status": new_status}},
        ip,
    )
    db.commit()

    return _reload_poc(db, poc.id)


# ── 克隆 ────────────────────────────────────────────────────────────────


def clone_poc(
    db: Session, poc_id: int, data: PocCloneRequest, user_id: int | None = None, ip: str | None = None
) -> Poc:
    """克隆 POC：复制内容 + 关联关系，使用新名称创建独立 POC。"""
    original = _get_poc_or_404(db, poc_id)

    # 检查新名称唯一性
    existing = db.scalar(select(Poc).where(Poc.name == data.name, Poc.source == original.source))
    if existing:
        raise AppError(ErrorCode.CONFLICT, f"名称 '{data.name}' 在来源 '{original.source}' 下已存在")

    # 克隆 POC
    poc_uuid = str(uuid.uuid4())
    new_poc = Poc(
        uuid=poc_uuid,
        name=data.name,
        title=original.title,
        description=original.description,
        severity=original.severity,
        format=original.format,
        language=original.language,
        content=original.content,
        content_hash=original.content_hash,
        author=original.author,
        source=original.source,
        status="draft",
        version=1,
        extra_meta=original.extra_meta,
        created_by=user_id,
        updated_by=user_id,
    )
    db.add(new_poc)
    db.flush()

    # 克隆标签关联
    for pt in original.tags:
        db.add(PocTag(poc_id=new_poc.id, tag_id=pt.tag_id))

    # 克隆 CVE 关联
    for pv in original.vulns:
        db.add(PocVuln(poc_id=new_poc.id, vuln_id=pv.vuln_id))

    # 克隆分类关联
    for pc in original.categories:
        db.add(PocCategory(poc_id=new_poc.id, category_id=pc.category_id))

    # 创建首条版本快照
    _create_version_snapshot(db, new_poc, user_id)

    db.flush()
    db.commit()

    # 事件 + 审计
    _publish_event("poc.created", str(new_poc.id), {"name": new_poc.name, "cloned_from": poc_id})
    _create_audit_log(
        db,
        user_id,
        "poc.created",
        "poc",
        str(new_poc.id),
        {"poc_name": new_poc.name, "cloned_from": original.name, "source": "clone"},
        ip,
    )
    db.commit()

    return _reload_poc(db, new_poc.id)


# ── 版本历史 ────────────────────────────────────────────────────────────


def get_poc_versions(db: Session, poc_id: int) -> list[PocVersion]:
    """获取 POC 所有版本历史，按版本序号降序排列。"""
    _get_poc_or_404(db, poc_id)  # 确认 POC 存在
    stmt = select(PocVersion).where(PocVersion.poc_id == poc_id).order_by(PocVersion.version_seq.desc())
    return list(db.scalars(stmt).all())


# ── 内部辅助 ────────────────────────────────────────────────────────────


def _sync_cve_ids(db: Session, poc: Poc, cve_ids: list[str]) -> None:
    """同步 POC 的 CVE 关联：删除旧关联，创建新关联（CVE 不存在时自动创建）。"""
    # 删除旧关联
    db.query(PocVuln).where(PocVuln.poc_id == poc.id).delete()

    for cve_id in cve_ids:
        cve_id = cve_id.strip().upper()
        if not cve_id:
            continue
        # 查找或创建 CVE 记录
        vuln = db.scalar(select(Vuln).where(Vuln.cve_id == cve_id))
        if vuln is None:
            vuln = Vuln(cve_id=cve_id)
            db.add(vuln)
            db.flush()
        db.add(PocVuln(poc_id=poc.id, vuln_id=vuln.id))


def _sync_tag_ids(db: Session, poc: Poc, tag_ids: list[int]) -> None:
    """同步 POC 的标签关联：删除旧关联，创建新关联。"""
    db.query(PocTag).where(PocTag.poc_id == poc.id).delete()
    for tag_id in tag_ids:
        tag = db.get(Tag, tag_id)
        if tag:
            db.add(PocTag(poc_id=poc.id, tag_id=tag_id))


def _sync_category_ids(db: Session, poc: Poc, category_ids: list[int]) -> None:
    """同步 POC 的分类关联：删除旧关联，创建新关联。"""
    db.query(PocCategory).where(PocCategory.poc_id == poc.id).delete()
    for cat_id in category_ids:
        cat = db.get(Category, cat_id)
        if cat:
            db.add(PocCategory(poc_id=poc.id, category_id=cat_id))


def _sync_affected_versions(db: Session, poc: Poc, versions: list[dict] | None) -> None:
    """同步 POC 的版本影响范围：删除旧关联，创建新关联。"""
    if versions is None:
        return
    db.query(PocAffected).where(PocAffected.poc_id == poc.id).delete()
    for v in versions:
        db.add(PocAffected(
            poc_id=poc.id,
            version_start=v.get("version_start"),
            version_start_type=v.get("version_start_type", ">="),
            version_end=v.get("version_end"),
            version_end_type=v.get("version_end_type", "<="),
        ))  # fmt: skip


def _create_version_snapshot(db: Session, poc: Poc, user_id: int | None = None) -> None:
    """创建当前版本的内容快照。

    首条快照 version_seq=1，后续递增。
    """
    max_seq = (
        db.scalar(
            select(func.coalesce(func.max(PocVersion.version_seq), 0)).where(PocVersion.poc_id == poc.id)
        )
        or 0
    )

    version = PocVersion(
        poc_id=poc.id,
        version_seq=max_seq + 1,
        content=poc.content,
        content_hash=poc.content_hash,
        changed_by=user_id,
        changed_at=dt.datetime.now(dt.timezone.utc),
    )
    db.add(version)


def _reload_poc(db: Session, poc_id: int) -> Poc:
    """重新加载 POC（含所有关联数据），返回最新状态。"""
    stmt = _load_poc_relations(select(Poc).where(Poc.id == poc_id))
    poc = db.scalar(stmt)
    if poc is None:
        raise NotFoundError("POC", str(poc_id))
    return poc


def _build_poc_list_item(poc: Poc) -> dict:
    """将 POC ORM 对象转换为列表项字典。"""
    return {
        "id": poc.id,
        "uuid": poc.uuid,
        "name": poc.name,
        "title": poc.title,
        "severity": poc.severity,
        "format": poc.format,
        "source": poc.source,
        "status": poc.status,
        "author": poc.author,
        "version": poc.version,
        "tags": _extract_tags(poc),
        "cve_ids": _extract_cve_ids(poc),
        "created_at": poc.created_at.isoformat() if poc.created_at else None,
        "updated_at": poc.updated_at.isoformat() if poc.updated_at else None,
    }


def _build_poc_detail(poc: Poc) -> dict:
    """将 POC ORM 对象转换为详情字典。"""
    return {
        "id": poc.id,
        "uuid": poc.uuid,
        "name": poc.name,
        "title": poc.title,
        "description": poc.description,
        "severity": poc.severity,
        "format": poc.format,
        "language": poc.language,
        "content": poc.content,
        "content_hash": poc.content_hash,
        "author": poc.author,
        "source": poc.source,
        "status": poc.status,
        "version": poc.version,
        "extra_meta": poc.extra_meta,
        "tags": _extract_tags(poc),
        "cve_ids": _extract_cve_ids(poc),
        "cnvd_ids": (poc.extra_meta or {}).get("cnvd_ids", []),
        "references": (poc.extra_meta or {}).get("references", []),
        "fofa_syntax": (poc.extra_meta or {}).get("fofa_syntax"),
        "shodan_syntax": (poc.extra_meta or {}).get("shodan_syntax"),
        "categories": _extract_categories(poc),
        "affected_versions": _extract_affected_versions(poc),
        "created_by": poc.created_by,
        "updated_by": poc.updated_by,
        "created_at": poc.created_at.isoformat() if poc.created_at else None,
        "updated_at": poc.updated_at.isoformat() if poc.updated_at else None,
    }
