"""add persons cpf foundation

Revision ID: 8e22c771dc42
Revises: 1c9d2e7b6f01
Create Date: 2026-04-24 12:17:11.909008
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "8e22c771dc42"
down_revision: Union[str, Sequence[str], None] = "1c9d2e7b6f01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "persons",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("cpf", sa.String(length=11), nullable=False),
        sa.Column("cpf_masked", sa.String(length=14), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("birth_date", sa.String(length=10), nullable=True),
        sa.Column("is_valid_cpf", sa.Boolean(), nullable=False),
        sa.Column("validation_status", sa.String(length=50), nullable=False),
        sa.Column("source", sa.String(length=80), nullable=False),
        sa.Column("consent_reference", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "cpf", name="uq_persons_tenant_cpf"),
    )
    op.create_index(
        "ix_persons_tenant_cpf",
        "persons",
        ["tenant_id", "cpf"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_persons_tenant_cpf", table_name="persons")
    op.drop_table("persons")
