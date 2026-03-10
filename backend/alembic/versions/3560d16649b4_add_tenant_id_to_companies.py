"""add tenant_id to companies

Revision ID: 3560d16649b4
Revises: 19ab383299b5
Create Date: 2026-03-09 19:19:06.628314

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "3560d16649b4"
down_revision: Union[str, Sequence[str], None] = "19ab383299b5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _is_sqlite() -> bool:
    return op.get_bind().dialect.name == "sqlite"


def upgrade() -> None:
    op.add_column("companies", sa.Column("tenant_id", sa.Integer(), nullable=True))
    op.execute("UPDATE companies SET tenant_id = 1 WHERE tenant_id IS NULL")

    if _is_sqlite():
        with op.batch_alter_table("companies") as batch_op:
            batch_op.alter_column("tenant_id", existing_type=sa.Integer(), nullable=False)
    else:
        op.alter_column("companies", "tenant_id", existing_type=sa.Integer(), nullable=False)

    op.create_index(op.f("ix_companies_tenant_id"), "companies", ["tenant_id"], unique=False)

    if not _is_sqlite():
        op.create_foreign_key(
            "fk_companies_tenant_id_tenants",
            "companies",
            "tenants",
            ["tenant_id"],
            ["id"],
            ondelete="CASCADE",
        )


def downgrade() -> None:
    if not _is_sqlite():
        op.drop_constraint("fk_companies_tenant_id_tenants", "companies", type_="foreignkey")
    op.drop_index(op.f("ix_companies_tenant_id"), table_name="companies")
    op.drop_column("companies", "tenant_id")
