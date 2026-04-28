"""make companies cnpj unique per tenant

Revision ID: 1c9d2e7b6f01
Revises: d434b0c621f9
Create Date: 2026-04-24 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op

revision: str = "1c9d2e7b6f01"
down_revision: Union[str, Sequence[str], None] = "d434b0c621f9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("companies") as batch_op:
        batch_op.drop_index("ix_companies_cnpj")
        batch_op.create_unique_constraint(
            "uq_companies_tenant_cnpj",
            ["tenant_id", "cnpj"],
        )


def downgrade() -> None:
    with op.batch_alter_table("companies") as batch_op:
        batch_op.drop_constraint(
            "uq_companies_tenant_cnpj",
            type_="unique",
        )
        batch_op.create_index(
            "ix_companies_cnpj",
            ["cnpj"],
            unique=True,
        )
