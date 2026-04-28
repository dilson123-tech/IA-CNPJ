"""add company qsa json field

Revision ID: d434b0c621f9
Revises: 8ed137c53b88
Create Date: 2026-04-23 22:16:12.091896
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d434b0c621f9"
down_revision: Union[str, Sequence[str], None] = "8ed137c53b88"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("companies", sa.Column("qsa", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("companies", "qsa")
