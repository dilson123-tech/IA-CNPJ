from datetime import date
from decimal import Decimal

from sqlalchemy import Boolean, Date, JSON, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Company(Base):
    __tablename__ = "companies"
    __table_args__ = (
        UniqueConstraint("tenant_id", "cnpj", name="uq_companies_tenant_cnpj"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    cnpj: Mapped[str] = mapped_column(String(14), index=True)
    razao_social: Mapped[str] = mapped_column(String(200))
    nome_fantasia: Mapped[str | None] = mapped_column(String(200), nullable=True)

    situacao_cadastral: Mapped[str | None] = mapped_column(String(50), nullable=True)
    data_situacao_cadastral: Mapped[date | None] = mapped_column(Date, nullable=True)
    descricao_motivo_situacao_cadastral: Mapped[str | None] = mapped_column(String(120), nullable=True)
    situacao_especial: Mapped[str | None] = mapped_column(String(120), nullable=True)
    data_situacao_especial: Mapped[date | None] = mapped_column(Date, nullable=True)

    natureza_juridica: Mapped[str | None] = mapped_column(String(120), nullable=True)
    codigo_natureza_juridica: Mapped[str | None] = mapped_column(String(10), nullable=True)
    porte: Mapped[str | None] = mapped_column(String(50), nullable=True)
    matriz_filial: Mapped[str | None] = mapped_column(String(20), nullable=True)
    opcao_pelo_simples: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    opcao_pelo_mei: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    capital_social: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)

    data_abertura: Mapped[date | None] = mapped_column(Date, nullable=True)
    data_baixa: Mapped[date | None] = mapped_column(Date, nullable=True)

    cnae_principal_codigo: Mapped[str | None] = mapped_column(String(20), nullable=True)
    cnae_principal_descricao: Mapped[str | None] = mapped_column(String(200), nullable=True)

    municipio: Mapped[str | None] = mapped_column(String(100), nullable=True)
    codigo_municipio_ibge: Mapped[str | None] = mapped_column(String(10), nullable=True)
    uf: Mapped[str | None] = mapped_column(String(2), nullable=True)
    cep: Mapped[str | None] = mapped_column(String(20), nullable=True)
    bairro: Mapped[str | None] = mapped_column(String(100), nullable=True)
    logradouro: Mapped[str | None] = mapped_column(String(150), nullable=True)
    numero: Mapped[str | None] = mapped_column(String(30), nullable=True)
    complemento: Mapped[str | None] = mapped_column(String(120), nullable=True)

    email: Mapped[str | None] = mapped_column(String(200), nullable=True)
    ddd_telefone_1: Mapped[str | None] = mapped_column(String(20), nullable=True)
    ddd_telefone_2: Mapped[str | None] = mapped_column(String(20), nullable=True)

    qsa: Mapped[list | None] = mapped_column(JSON, nullable=True)

    tenant_id: Mapped[int] = mapped_column(nullable=False, index=True)
