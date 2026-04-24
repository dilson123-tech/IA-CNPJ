"""add company public registry fields

Revision ID: 8ed137c53b88
Revises: 8f806ebf878b
Create Date: 2026-04-23 13:15:21.153261
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "8ed137c53b88"
down_revision: Union[str, Sequence[str], None] = "8f806ebf878b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("companies", sa.Column("data_situacao_cadastral", sa.Date(), nullable=True))
    op.add_column("companies", sa.Column("descricao_motivo_situacao_cadastral", sa.String(length=120), nullable=True))
    op.add_column("companies", sa.Column("situacao_especial", sa.String(length=120), nullable=True))
    op.add_column("companies", sa.Column("data_situacao_especial", sa.Date(), nullable=True))
    op.add_column("companies", sa.Column("codigo_natureza_juridica", sa.String(length=10), nullable=True))
    op.add_column("companies", sa.Column("codigo_municipio_ibge", sa.String(length=10), nullable=True))
    op.add_column("companies", sa.Column("cep", sa.String(length=20), nullable=True))
    op.add_column("companies", sa.Column("bairro", sa.String(length=100), nullable=True))
    op.add_column("companies", sa.Column("logradouro", sa.String(length=150), nullable=True))
    op.add_column("companies", sa.Column("numero", sa.String(length=30), nullable=True))
    op.add_column("companies", sa.Column("complemento", sa.String(length=120), nullable=True))
    op.add_column("companies", sa.Column("email", sa.String(length=200), nullable=True))
    op.add_column("companies", sa.Column("ddd_telefone_1", sa.String(length=20), nullable=True))
    op.add_column("companies", sa.Column("ddd_telefone_2", sa.String(length=20), nullable=True))


def downgrade() -> None:
    op.drop_column("companies", "ddd_telefone_2")
    op.drop_column("companies", "ddd_telefone_1")
    op.drop_column("companies", "email")
    op.drop_column("companies", "complemento")
    op.drop_column("companies", "numero")
    op.drop_column("companies", "logradouro")
    op.drop_column("companies", "bairro")
    op.drop_column("companies", "cep")
    op.drop_column("companies", "codigo_municipio_ibge")
    op.drop_column("companies", "codigo_natureza_juridica")
    op.drop_column("companies", "data_situacao_especial")
    op.drop_column("companies", "situacao_especial")
    op.drop_column("companies", "descricao_motivo_situacao_cadastral")
    op.drop_column("companies", "data_situacao_cadastral")
