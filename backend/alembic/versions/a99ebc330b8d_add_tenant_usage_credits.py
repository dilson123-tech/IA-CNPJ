"""add tenant usage credits

Revision ID: a99ebc330b8d
Revises: 8e22c771dc42
Create Date: 2026-04-26 17:38:13.759372
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a99ebc330b8d"
down_revision: Union[str, Sequence[str], None] = "8e22c771dc42"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tenant_usage_credits",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("balance", sa.Integer(), nullable=False),
        sa.Column("consumed", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=80), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", name="uq_tenant_usage_credits_tenant_id"),
    )
    op.create_index(
        "ix_tenant_usage_credits_id",
        "tenant_usage_credits",
        ["id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_tenant_usage_credits_id", table_name="tenant_usage_credits")
    op.drop_table("tenant_usage_credits")
