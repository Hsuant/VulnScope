"""数据库初始化：一次初始化即构建 VulnScope 完整数据库结构（全部表与字段）。

策略
----
ORM 模型（``app/models/``）是表和字段的**唯一真相**（Single Source of Truth）。
本模块通过 ``Base.metadata.create_all`` 按模型元数据一次性创建全部表、字段、
索引与约束，**不写入任何种子数据**。不再使用 Alembic 迁移历史
（``backend/alembic/`` 及其 ``alembic_version`` 表已删除）。

用法
----
- 应用启动时：FastAPI lifespan 调用 ``init_db()``（幂等，仅建缺失表）。
- 命令行手动初始化：

    python -m app.db.init_db             # 仅建缺失表（不写种子数据，幂等）
    python -m app.db.init_db --reset     # 清空并重建全部表（开发用，会丢数据）

注意：``create_all`` 只创建「不存在」的表，不会给已存在的表补列/改约束。
所以当模型字段变更时，开发库需 ``--reset`` 或删除 ``.db`` 文件后重启。
内置角色与默认管理员由应用启动（``app/main.py`` lifespan）按需创建，不在本命令产出。
"""

from __future__ import annotations

import argparse
import logging
import sys

from sqlalchemy import Engine, inspect

import app.models  # noqa: F401  （导入即注册全部 ORM 模型到 Base.metadata）
from app.db.base import Base
from app.db.session import engine

logger = logging.getLogger(__name__)

# ── 完整 schema 清单（18 张表）：表名 → 模型类 → 字段列表 ─────────────────
# 字段定义以 ORM 模型为准（类型/长度/约束/索引/外键），此处只作说明与校验清单。
SCHEMA_MANIFEST: dict[str, dict] = {
    # 认证与权限（app/models/user.py）
    "user": {
        "model": "User",
        "purpose": "用户账号表（应用登录主体）",
        "fields": [
            "id",
            "username",
            "email",
            "password_hash",
            "role_id",
            "is_active",
            "last_login_at",
            "created_at",
            "updated_at",
        ],
    },
    "role": {
        "model": "Role",
        "purpose": "角色表（viewer / editor / admin，RBAC 权限矩阵）",
        "fields": ["id", "name", "description", "permissions"],
    },
    # POC 核心（app/models/poc.py）
    "poc": {
        "model": "Poc",
        "purpose": "POC 主表（名称、格式、内容、状态、版本、来源、作者）",
        "fields": [
            "id",
            "uuid",
            "name",
            "title",
            "description",
            "severity",
            "format",
            "language",
            "content",
            "content_hash",
            "author",
            "source",
            "status",
            "version",
            "extra_meta",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ],
    },
    "poc_version": {
        "model": "PocVersion",
        "purpose": "POC 内容历史版本快照（保存时生成）",
        "fields": ["id", "poc_id", "version_seq", "content", "content_hash", "changed_by", "changed_at"],
    },
    "vuln": {
        "model": "Vuln",
        "purpose": "CVE 漏洞实体（编号、厂商、评分、受影响产品、修复建议、参考链接）",
        "fields": [
            "id",
            "cve_id",
            "vendor",
            "title",
            "description",
            "cvss",
            "severity",
            "cvss_metrics",
            "product",
            "remediation",
            "reference",
            "created_at",
            "updated_at",
        ],
    },
    "poc_vuln": {
        "model": "PocVuln",
        "purpose": "POC ↔ CVE 多对多关联（复合主键）",
        "fields": ["poc_id", "vuln_id"],
    },
    # 标签与分类
    "tag": {
        "model": "Tag",
        "purpose": "标签字典（namespace:name 唯一，含颜色/描述）",
        "fields": ["id", "namespace", "name", "color", "description"],
    },
    "poc_tag": {
        "model": "PocTag",
        "purpose": "POC ↔ 标签多对多关联（复合主键）",
        "fields": ["poc_id", "tag_id"],
    },
    "category": {
        "model": "Category",
        "purpose": "树形分类（自引用 category.parent_id，含层级与排序）",
        "fields": ["id", "parent_id", "name", "slug", "description", "level", "sort_order"],
    },
    "poc_category": {
        "model": "PocCategory",
        "purpose": "POC ↔ 分类多对多关联（复合主键）",
        "fields": ["poc_id", "category_id"],
    },
    # 厂商-产品-组件 资产模型
    "vendor": {
        "model": "Vendor",
        "purpose": "厂商（组织/公司，含主页与描述）",
        "fields": ["id", "name", "slug", "homepage", "description", "created_at", "updated_at"],
    },
    "product": {
        "model": "Product",
        "purpose": "产品（隶属厂商，含分类/主页/Logo）",
        "fields": [
            "id",
            "vendor_id",
            "name",
            "slug",
            "category",
            "homepage",
            "description",
            "logo",
            "created_at",
            "updated_at",
        ],
    },
    "component": {
        "model": "Component",
        "purpose": "子组件（隶属产品）",
        "fields": ["id", "product_id", "name", "slug", "description", "created_at", "updated_at"],
    },
    "poc_affected": {
        "model": "PocAffected",
        "purpose": "POC 版本影响范围（起止版本区间与边界类型）",
        "fields": [
            "id",
            "poc_id",
            "product_id",
            "component_id",
            "version_start",
            "version_start_type",
            "version_end",
            "version_end_type",
            "version_expression",
            "created_at",
            "updated_at",
        ],
    },
    # 执行与溯源
    "poc_deployment": {
        "model": "PocDeployment",
        "purpose": "POC 执行元信息（攻击向量/协议/端口等，v2 验证模块预留）",
        "fields": [
            "id",
            "poc_id",
            "attack_vector",
            "auth_required",
            "auth_role",
            "protocol",
            "default_port",
            "requires_interaction",
            "safe_to_run",
            "extra_meta",
        ],
    },
    "poc_source_record": {
        "model": "PocSourceRecord",
        "purpose": "来源溯源留痕（批量批次/源 URL/引用 ID/抓取时间）",
        "fields": [
            "id",
            "poc_id",
            "source_type",
            "batch_id",
            "source_url",
            "ref_id",
            "fetched_at",
            "extra_meta",
        ],
    },
    "poc_attachment": {
        "model": "PocAttachment",
        "purpose": "POC 附属文件（路径/类型/大小/SHA-256）",
        "fields": ["id", "poc_id", "file_name", "file_path", "file_type", "size", "sha256"],
    },
    "audit_log": {
        "model": "AuditLog",
        "purpose": "操作审计日志（动作/资源/明细 JSON/来源 IP/时间）",
        "fields": ["id", "user_id", "action", "resource_type", "resource_id", "detail", "ip", "created_at"],
    },
}


def ensure_schema(bind: Engine = engine) -> None:
    """按模型元数据创建全部缺失的表（幂等，不破坏已有数据）。

    全部表与字段、索引、唯一约束、外键均由 ORM 模型生成
    （``app/models/__init__.py`` 导入即完成注册）。
    """
    Base.metadata.create_all(bind=bind)


def _verify_schema(bind: Engine = engine) -> None:
    """核对清单中的全部表已实际建成，缺失则抛出（防止模型未注册导致漏表）。"""
    existing = set(inspect(bind).get_table_names())
    missing = [name for name in SCHEMA_MANIFEST if name not in existing]
    if missing:
        raise RuntimeError(
            f"数据库初始化不完整，缺少以下表: {', '.join(missing)}。"
            "请确认 app/models/ 中对应模型已定义并被 app.models 导入。"
        )


def init_db(reset: bool = False) -> None:
    """初始化完整数据库结构 = 建全量表（含字段/索引/约束）。

    仅建结构，不写入任何数据（角色/管理员等由应用启动按需创建）。

    Args:
        reset: 为 True 时先 drop_all 清空再重建（开发用，会丢失全部数据）。
    """
    if reset:
        Base.metadata.drop_all(bind=engine)
    ensure_schema()
    _verify_schema()


def main(argv: list[str] | None = None) -> int:
    """命令行入口：构建 VulnScope 完整数据库结构（仅建表，不含种子数据）。"""
    parser = argparse.ArgumentParser(description="构建 VulnScope 完整数据库结构（全部表，不含种子数据）")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="清空并重建全部表（开发用，会丢失数据）",
    )
    args = parser.parse_args(argv)
    init_db(reset=args.reset)
    suffix = "（已重置清空重建）" if args.reset else ""
    logger.info("数据库结构初始化完成%s，共 %d 张表（不含种子数据）", suffix, len(SCHEMA_MANIFEST))
    return 0


if __name__ == "__main__":
    sys.exit(main())
