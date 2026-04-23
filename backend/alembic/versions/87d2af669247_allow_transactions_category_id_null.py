"""allow transactions category_id null

Revision ID: 87d2af669247
Revises: c4f2e9a1b7d0
Create Date: 2026-04-23
"""

from alembic import op
import sqlalchemy as sa


revision = "87d2af669247"
down_revision = "c4f2e9a1b7d0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("transactions") as batch_op:
        batch_op.alter_column(
            "category_id",
            existing_type=sa.Integer(),
            nullable=True,
        )


def downgrade() -> None:
    with op.batch_alter_table("transactions") as batch_op:
        batch_op.alter_column(
            "category_id",
            existing_type=sa.Integer(),
            nullable=False,
        )
