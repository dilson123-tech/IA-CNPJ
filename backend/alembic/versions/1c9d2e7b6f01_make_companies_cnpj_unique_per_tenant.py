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
    op.drop_index("ix_companies_cnpj", table_name="companies")
    op.create_unique_constraint(
        "uq_companies_tenant_cnpj",
        "companies",
        ["tenant_id", "cnpj"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_companies_tenant_cnpj", "companies", type_="unique")
    op.create_index("ix_companies_cnpj", "companies", ["cnpj"], unique=True)
