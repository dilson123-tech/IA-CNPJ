"""add credit purchases

Revision ID: a8ca1ad6d0d2
Revises: a99ebc330b8d
Create Date: 2026-04-27 11:58:02.945621
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a8ca1ad6d0d2"
down_revision: Union[str, Sequence[str], None] = "a99ebc330b8d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "credit_purchases",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("package_code", sa.String(length=50), nullable=False),
        sa.Column("credits_amount", sa.Integer(), nullable=False),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(length=10), nullable=False),
        sa.Column("provider", sa.String(length=30), nullable=False),
        sa.Column("billing_type", sa.String(length=30), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("provider_reference", sa.String(length=120), nullable=True),
        sa.Column("payment_url", sa.String(length=500), nullable=True),
        sa.Column("customer_name", sa.String(length=255), nullable=True),
        sa.Column("customer_email", sa.String(length=255), nullable=True),
        sa.Column("customer_cpf_cnpj", sa.String(length=20), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_credit_purchases_id", "credit_purchases", ["id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_credit_purchases_id", table_name="credit_purchases")
    op.drop_table("credit_purchases")
