"""add tenant_id to categories

Revision ID: a95a3390e4c4
Revises: 3560d16649b4
Create Date: 2026-03-10

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a95a3390e4c4"
down_revision: Union[str, Sequence[str], None] = "3560d16649b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("categories", sa.Column("tenant_id", sa.Integer(), nullable=True))
    op.create_index(op.f("ix_categories_tenant_id"), "categories", ["tenant_id"], unique=False)
    op.create_foreign_key(
        "fk_categories_tenant_id_tenants",
        "categories",
        "tenants",
        ["tenant_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.execute("UPDATE categories SET tenant_id = 1 WHERE tenant_id IS NULL")
    op.alter_column("categories", "tenant_id", nullable=False)


def downgrade() -> None:
    op.drop_constraint("fk_categories_tenant_id_tenants", "categories", type_="foreignkey")
    op.drop_index(op.f("ix_categories_tenant_id"), table_name="categories")
    op.drop_column("categories", "tenant_id")
