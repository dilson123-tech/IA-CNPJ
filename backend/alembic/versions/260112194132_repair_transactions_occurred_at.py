"""repair transactions occurred_at drift

Revision ID: 260112194132
Revises: 2fa25a38909e
Create Date: 2026-01-12T19:41:32
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "260112194132"
down_revision = "2fa25a38909e"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    insp = inspect(bind)

    # se a tabela nem existir, não faz nada (mas isso seria outro problema)
    tables = set(insp.get_table_names())
    if "transactions" not in tables:
        return

    cols = [c["name"] for c in insp.get_columns("transactions")]
    if "occurred_at" not in cols:
        op.add_column("transactions", sa.Column("occurred_at", sa.DateTime(), nullable=True))


def downgrade():
    # SQLite não dropa coluna facilmente; no-op
    pass
