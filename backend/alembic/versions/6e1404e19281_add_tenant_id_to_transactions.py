"""add tenant_id to transactions

Revision ID: 6e1404e19281
Revises: a95a3390e4c4
Create Date: 2026-03-10

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "6e1404e19281"
down_revision: Union[str, Sequence[str], None] = "a95a3390e4c4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _is_sqlite() -> bool:
    return op.get_bind().dialect.name == "sqlite"


def upgrade() -> None:
    op.add_column("transactions", sa.Column("tenant_id", sa.Integer(), nullable=True))
    op.execute("UPDATE transactions SET tenant_id = 1 WHERE tenant_id IS NULL")

    if _is_sqlite():
        with op.batch_alter_table("transactions") as batch_op:
            batch_op.alter_column("tenant_id", existing_type=sa.Integer(), nullable=False)
    else:
        op.alter_column("transactions", "tenant_id", existing_type=sa.Integer(), nullable=False)

    op.create_index(op.f("ix_transactions_tenant_id"), "transactions", ["tenant_id"], unique=False)

    if not _is_sqlite():
        op.create_foreign_key(
            "fk_transactions_tenant_id_tenants",
            "transactions",
            "tenants",
            ["tenant_id"],
            ["id"],
            ondelete="CASCADE",
        )


def downgrade() -> None:
    if not _is_sqlite():
        op.drop_constraint("fk_transactions_tenant_id_tenants", "transactions", type_="foreignkey")
    op.drop_index(op.f("ix_transactions_tenant_id"), table_name="transactions")
    op.drop_column("transactions", "tenant_id")
