from typing import Optional, List

from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel, Field, AliasChoices, ConfigDict, model_validator

from app.schemas.reports import Period, Totals, CategoryBreakdown, TransactionBrief


class PeriodIn(BaseModel):
    start: str | None = None
    end: str | None = None


class CompanySummary(BaseModel):
    cnpj: str
    razao_social: str
    nome_fantasia: str | None = None

    situacao_cadastral: str | None = None
    data_situacao_cadastral: date | None = None
    descricao_motivo_situacao_cadastral: str | None = None
    situacao_especial: str | None = None
    data_situacao_especial: date | None = None

    empresa_aberta: bool | None = None

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

    qsa: list[dict] | None = None


class AiConsultRequest(BaseModel):
    company_id: int = Field(..., ge=1)
    period: PeriodIn | None = None
    start: str | None = Field(None, description="YYYY-MM-DD ou ISO datetime")
    end: str | None = Field(None, description="YYYY-MM-DD ou ISO datetime")
    limit: int = Field(20, ge=1, le=200)
    question: str | None = Field(None, description="Pergunta opcional do usuário")

    @model_validator(mode="after")
    def _normalize_period(self):
        if getattr(self, "period", None):
            if not getattr(self, "start", None) and self.period.start:
                self.start = self.period.start
            if not getattr(self, "end", None) and self.period.end:
                self.end = self.period.end

        if getattr(self, "start_date", None) and not getattr(self, "start", None):
            self.start = self.start_date
        if getattr(self, "end_date", None) and not getattr(self, "end", None):
            self.end = self.end_date

        return self


class AiConsultResponse(BaseModel):
    company_id: int
    period: Period
    generated_at: datetime

    headline: str
    insights: list[str]
    risks: list[str]
    actions: list[str]

    company_summary: CompanySummary | None = None
    numbers: Totals
    top_categories: list[CategoryBreakdown]
    recent_transactions: list[TransactionBrief]


class AIPeriod(BaseModel):
    start: str = Field(..., description="YYYY-MM-DD")
    end: str = Field(..., description="YYYY-MM-DD")


class AISuggestCategoriesRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    company_id: int
    start: str = Field(validation_alias=AliasChoices("start", "start_date"))
    end: str = Field(validation_alias=AliasChoices("end", "end_date"))
    limit: int = 200
    include_no_match: bool = False


class AISuggestedItem(BaseModel):
    id: int
    suggested_category_id: Optional[int] = None
    confidence: float = 0.0
    rule: str = "no_match"
    description: str = ""

    reason: str = ""
    provider: str = "rule-based"
    signals: list[str] = Field(default_factory=list)


class AISuggestCategoriesResponse(BaseModel):
    company_id: int
    period: AIPeriod
    items: List[AISuggestedItem] = []


class AIApplySuggestionsRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    company_id: int = Field(..., ge=1)
    start: str | None = Field(default=None, validation_alias=AliasChoices("start", "start_date"))
    end: str | None = Field(default=None, validation_alias=AliasChoices("end", "end_date"))
    limit: int = Field(200, ge=1, le=500)
    dry_run: bool = False
    include_no_match: bool = False


class AIApplySuggestionsResponse(BaseModel):
    company_id: int
    period: dict
    dry_run: bool
    suggested: int
    updated: int
    items: list[AISuggestedItem] = []
    missing_ids: list[int] = []
    skipped_ids: list[int] = []
    invalid_category_ids: list[int] = []
