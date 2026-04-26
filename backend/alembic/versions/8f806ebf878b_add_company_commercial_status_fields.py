"""add company commercial status fields

Revision ID: 8f806ebf878b
Revises: 376e49cd1ba6
Create Date: 2026-04-23 10:47:48.552036
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "8f806ebf878b"
down_revision: Union[str, Sequence[str], None] = "376e49cd1ba6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("companies", sa.Column("matriz_filial", sa.String(length=20), nullable=True))
    op.add_column("companies", sa.Column("opcao_pelo_simples", sa.Boolean(), nullable=True))
    op.add_column("companies", sa.Column("opcao_pelo_mei", sa.Boolean(), nullable=True))
    op.add_column("companies", sa.Column("capital_social", sa.Numeric(precision=18, scale=2), nullable=True))


def downgrade() -> None:
    op.drop_column("companies", "capital_social")
    op.drop_column("companies", "opcao_pelo_mei")
    op.drop_column("companies", "opcao_pelo_simples")
    op.drop_column("companies", "matriz_filial")
