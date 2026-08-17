"""add vuln detail fields

为 vuln 表新增 CVE 详情字段：
- cvss_metric: CVSS 指标向量（如 "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"）
- affected: 受影响产品列表（JSON 数组）
- remediation: 修复建议（JSON，含 mitigation 官方补丁 / workaround 临时方案）
- reference: 参考链接（JSON 数组）

Revision ID: a1b2c3d4e5f6
Revises: f0a1c2b3d4e5
Create Date: 2026-08-18 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = 'a1b2c3d4e5f6'
down_revision = 'f0a1c2b3d4e5'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # SQLite 新增列走 batch 模式以兼容，JSON 字段均允许为空
    with op.batch_alter_table('vuln', schema=None) as batch_op:
        batch_op.add_column(sa.Column('cvss_metrics', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('product', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('remediation', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('reference', sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('vuln', schema=None) as batch_op:
        batch_op.drop_column('reference')
        batch_op.drop_column('remediation')
        batch_op.drop_column('product')
        batch_op.drop_column('cvss_metrics')
