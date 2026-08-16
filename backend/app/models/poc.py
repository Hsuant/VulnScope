"""POC 核心模型及相关关联表（开发方案 §5.3 ~ §5.8）。"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import (
    CHAR,
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db.base import Base, IntPKMixin, TimestampMixin


class Poc(Base, IntPKMixin, TimestampMixin):
    """POC 主表（§5.3）。"""

    __tablename__ = "poc"

    uuid: Mapped[str] = mapped_column(CHAR(36), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    severity: Mapped[str] = mapped_column(String(16), nullable=False, default="info", index=True)
    format: Mapped[str] = mapped_column(String(32), nullable=False, default="nuclei", index=True)
    language: Mapped[str | None] = mapped_column(String(32), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(CHAR(64), nullable=False, index=True)
    author: Mapped[str | None] = mapped_column(String(128), nullable=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="manual", index=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft", index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    extra_meta: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict)

    created_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("user.id"), nullable=True)
    updated_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("user.id"), nullable=True)

    # 关联
    versions: Mapped[list[PocVersion]] = relationship(back_populates="poc", cascade="all, delete-orphan")
    tags: Mapped[list[PocTag]] = relationship(back_populates="poc", cascade="all, delete-orphan")
    categories: Mapped[list[PocCategory]] = relationship(back_populates="poc", cascade="all, delete-orphan")
    vulns: Mapped[list[PocVuln]] = relationship(back_populates="poc", cascade="all, delete-orphan")
    affected: Mapped[list[PocAffected]] = relationship(back_populates="poc", cascade="all, delete-orphan")
    source_records: Mapped[list[PocSourceRecord]] = relationship(
        back_populates="poc", cascade="all, delete-orphan"
    )
    attachments: Mapped[list[PocAttachment]] = relationship(
        back_populates="poc", cascade="all, delete-orphan"
    )


class PocVersion(Base, IntPKMixin):
    """POC 内容历史版本快照（§5.8）。"""

    __tablename__ = "poc_version"

    poc_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("poc.id"), nullable=False, index=True)
    version_seq: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(CHAR(64), nullable=False)
    changed_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("user.id"), nullable=True)
    changed_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    poc: Mapped[Poc] = relationship(back_populates="versions")


class Vuln(Base, IntPKMixin, TimestampMixin):
    """CVE 漏洞实体（§5.8）。"""

    __tablename__ = "vuln"

    cve_id: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    cvss: Mapped[float | None] = mapped_column(nullable=True)
    severity: Mapped[str | None] = mapped_column(String(16), nullable=True, index=True)

    pocs: Mapped[list[PocVuln]] = relationship(back_populates="vuln", cascade="all, delete-orphan")


class PocVuln(Base):
    """POC↔CVE 多对多关联（§5.8）。"""

    __tablename__ = "poc_vuln"

    poc_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("poc.id"), primary_key=True)
    vuln_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("vuln.id"), primary_key=True)

    poc: Mapped[Poc] = relationship(back_populates="vulns")
    vuln: Mapped[Vuln] = relationship(back_populates="pocs")


class Tag(Base, IntPKMixin):
    """标签字典（§5.6）。"""

    __tablename__ = "tag"

    __table_args__ = (
        UniqueConstraint("namespace", "name", name="uq_tag_namespace_name"),
        {"sqlite_autoincrement": True},
    )

    namespace: Mapped[str] = mapped_column(String(32), nullable=False, default="general")
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    color: Mapped[str | None] = mapped_column(String(7), nullable=True)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)


class PocTag(Base):
    """POC↔标签多对多（§5.8）。"""

    __tablename__ = "poc_tag"

    poc_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("poc.id"), primary_key=True)
    tag_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("tag.id"), primary_key=True)

    poc: Mapped[Poc] = relationship(back_populates="tags")
    tag: Mapped[Tag] = relationship()


class Category(Base, IntPKMixin):
    """树形分类（§5.5）。"""

    __tablename__ = "category"

    parent_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("category.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    slug: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    level: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # 自引用树形结构：parent 是 many-to-one（子→父），children 是 one-to-many（父→子）
    parent: Mapped[Category | None] = relationship(back_populates="children", remote_side="Category.id")
    children: Mapped[list[Category]] = relationship(back_populates="parent", cascade="all")


class PocCategory(Base):
    """POC↔分类多对多（§5.5）。"""

    __tablename__ = "poc_category"

    poc_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("poc.id"), primary_key=True)
    category_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("category.id"), primary_key=True)

    poc: Mapped[Poc] = relationship(back_populates="categories")
    category: Mapped[Category] = relationship()


class Vendor(Base, IntPKMixin, TimestampMixin):
    """厂商（§5.2）。"""

    __tablename__ = "vendor"

    name: Mapped[str] = mapped_column(String(128), nullable=False)
    slug: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    homepage: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    products: Mapped[list[Product]] = relationship(back_populates="vendor", cascade="all, delete-orphan")


class Product(Base, IntPKMixin, TimestampMixin):
    """产品（§5.2）。"""

    __tablename__ = "product"

    vendor_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("vendor.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    slug: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    homepage: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    logo: Mapped[str | None] = mapped_column(String(255), nullable=True)

    vendor: Mapped[Vendor] = relationship(back_populates="products")
    components: Mapped[list[Component]] = relationship(back_populates="product", cascade="all, delete-orphan")


class Component(Base, IntPKMixin, TimestampMixin):
    """子组件（§5.2）。"""

    __tablename__ = "component"

    product_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("product.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    slug: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    product: Mapped[Product] = relationship(back_populates="components")


class PocAffected(Base, IntPKMixin, TimestampMixin):
    """版本影响范围（§5.4）。"""

    __tablename__ = "poc_affected"

    poc_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("poc.id"), nullable=False, index=True)
    product_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("product.id"), nullable=True)
    component_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("component.id"), nullable=True)
    version_start: Mapped[str | None] = mapped_column(String(32), nullable=True)
    version_start_type: Mapped[str] = mapped_column(String(8), nullable=False, default="any")
    version_end: Mapped[str | None] = mapped_column(String(32), nullable=True)
    version_end_type: Mapped[str] = mapped_column(String(8), nullable=False, default="any")
    version_expression: Mapped[str | None] = mapped_column(String(255), nullable=True)

    poc: Mapped[Poc] = relationship(back_populates="affected")


class PocDeployment(Base, IntPKMixin):
    """POC 执行元信息（§5.7，v2 预留）。"""

    __tablename__ = "poc_deployment"

    poc_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("poc.id"), nullable=False, unique=True)
    attack_vector: Mapped[str | None] = mapped_column(String(32), nullable=True)
    auth_required: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    auth_role: Mapped[str | None] = mapped_column(String(32), nullable=True)
    protocol: Mapped[str | None] = mapped_column(String(32), nullable=True)
    default_port: Mapped[int | None] = mapped_column(Integer, nullable=True)
    requires_interaction: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    safe_to_run: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    extra_meta: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class PocSourceRecord(Base, IntPKMixin):
    """来源溯源留痕（§5.8）。"""

    __tablename__ = "poc_source_record"

    poc_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("poc.id"), nullable=False, index=True)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    batch_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    source_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    ref_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    fetched_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    extra_meta: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    poc: Mapped[Poc] = relationship(back_populates="source_records")


class PocAttachment(Base, IntPKMixin):
    """附属文件（§5.8）。"""

    __tablename__ = "poc_attachment"

    poc_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("poc.id"), nullable=False, index=True)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    file_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    size: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    sha256: Mapped[str | None] = mapped_column(CHAR(64), nullable=True)

    poc: Mapped[Poc] = relationship(back_populates="attachments")


class AuditLog(Base, IntPKMixin):
    """操作审计日志（§5.8）。"""

    __tablename__ = "audit_log"

    user_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("user.id"), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    resource_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    detail: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    ip: Mapped[str | None] = mapped_column(String(45), nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
