"""add occurred_at to transactions

Revision ID: 2fa25a38909e
Revises: 42704e69e1f5
Create Date: 2026-01-06 22:10:31.675390

"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = '2fa25a38909e'
down_revision: Union[str, Sequence[str], None] = '42704e69e1f5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass



def downgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    cols = [c["name"] for c in insp.get_columns("transactions")]
    idx = [i["name"] for i in insp.get_indexes("transactions")]

    if "ix_transactions_occurred_at" in idx:
        op.drop_index("ix_transactions_occurred_at", table_name="transactions")
    if "occurred_at" in cols:
        op.drop_column("transactions", "occurred_at")

