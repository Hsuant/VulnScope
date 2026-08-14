"""poc_affected.product_id nullable

POC 受影响版本表单只收集版本区间、不绑定具体产品，故放开 product_id
非空约束，允许仅记录版本范围。

Revision ID: f0a1c2b3d4e5
Revises: ddceb963fe87
Create Date: 2026-08-15 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = 'f0a1c2b3d4e5'
down_revision = 'ddceb963fe87'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # SQLite 不支持直接改列约束，走 batch（表重建）模式
    with op.batch_alter_table('poc_affected', schema=None) as batch_op:
        batch_op.alter_column(
            'product_id',
            existing_type=sa.BigInteger(),
            nullable=True,
        )


def downgrade() -> None:
    with op.batch_alter_table('poc_affected', schema=None) as batch_op:
        batch_op.alter_column(
            'product_id',
            existing_type=sa.BigInteger(),
            nullable=False,
        )
