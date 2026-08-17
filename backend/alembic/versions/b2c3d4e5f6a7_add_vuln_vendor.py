"""add vuln vendor

为 vuln 表新增 vendor 列：标识漏洞所影响软件的开发厂商
（公司/组织），如 "Apache"、"Microsoft"。

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-08-18 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = 'b2c3d4e5f6a7'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('vuln', schema=None) as batch_op:
        batch_op.add_column(sa.Column('vendor', sa.String(length=128), nullable=True))
        batch_op.create_index('ix_vuln_vendor', ['vendor'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('vuln', schema=None) as batch_op:
        batch_op.drop_index('ix_vuln_vendor', table_name='vuln')
        batch_op.drop_column('vendor')
