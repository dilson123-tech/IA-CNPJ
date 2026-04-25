from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class CompanyCreate(BaseModel):
    cnpj: str = Field(min_length=14, max_length=14)
    razao_social: str


class CompanyOut(BaseModel):
    id: int
    cnpj: str
    razao_social: str
    nome_fantasia: str | None = None

    situacao_cadastral: str | None = None
    data_situacao_cadastral: date | None = None
    descricao_motivo_situacao_cadastral: str | None = None
    situacao_especial: str | None = None
    data_situacao_especial: date | None = None

    natureza_juridica: str | None = None
    codigo_natureza_juridica: str | None = None
    porte: str | None = None
    matriz_filial: str | None = None
    opcao_pelo_simples: bool | None = None
    opcao_pelo_mei: bool | None = None
    capital_social: Decimal | None = None

    data_abertura: date | None = None
    data_baixa: date | None = None

    cnae_principal_codigo: str | None = None
    cnae_principal_descricao: str | None = None

    municipio: str | None = None
    codigo_municipio_ibge: str | None = None
    uf: str | None = None
    cep: str | None = None
    bairro: str | None = None
    logradouro: str | None = None
    numero: str | None = None
    complemento: str | None = None

    email: str | None = None
    ddd_telefone_1: str | None = None
    ddd_telefone_2: str | None = None

    qsa: list | None = None

    model_config = ConfigDict(from_attributes=True)
