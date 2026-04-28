"""add credit purchase apply field

Revision ID: 920886c5b127
Revises: a8ca1ad6d0d2
Create Date: 2026-04-27 19:10:54.898867
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "920886c5b127"
down_revision: Union[str, Sequence[str], None] = "a8ca1ad6d0d2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "credit_purchases",
        sa.Column("credits_applied_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("credit_purchases", "credits_applied_at")
