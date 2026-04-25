"""add company business summary fields

Revision ID: 376e49cd1ba6
Revises: 87d2af669247
Create Date: 2026-04-23 08:07:18.315100
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "376e49cd1ba6"
down_revision: Union[str, Sequence[str], None] = "87d2af669247"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("companies", sa.Column("nome_fantasia", sa.String(length=200), nullable=True))
    op.add_column("companies", sa.Column("situacao_cadastral", sa.String(length=50), nullable=True))
    op.add_column("companies", sa.Column("natureza_juridica", sa.String(length=120), nullable=True))
    op.add_column("companies", sa.Column("porte", sa.String(length=50), nullable=True))
    op.add_column("companies", sa.Column("data_abertura", sa.Date(), nullable=True))
    op.add_column("companies", sa.Column("data_baixa", sa.Date(), nullable=True))
    op.add_column("companies", sa.Column("cnae_principal_codigo", sa.String(length=20), nullable=True))
    op.add_column("companies", sa.Column("cnae_principal_descricao", sa.String(length=200), nullable=True))
    op.add_column("companies", sa.Column("municipio", sa.String(length=100), nullable=True))
    op.add_column("companies", sa.Column("uf", sa.String(length=2), nullable=True))


def downgrade() -> None:
    op.drop_column("companies", "uf")
    op.drop_column("companies", "municipio")
    op.drop_column("companies", "cnae_principal_descricao")
    op.drop_column("companies", "cnae_principal_codigo")
    op.drop_column("companies", "data_baixa")
    op.drop_column("companies", "data_abertura")
    op.drop_column("companies", "porte")
    op.drop_column("companies", "natureza_juridica")
    op.drop_column("companies", "situacao_cadastral")
    op.drop_column("companies", "nome_fantasia")
