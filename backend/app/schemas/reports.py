from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field


class Period(BaseModel):
    start: str = Field(description="YYYY-MM-DD")
    end: str = Field(description="YYYY-MM-DD")


class Totals(BaseModel):
    entradas_cents: int
    saidas_cents: int
    saldo_cents: int
    qtd_transacoes: int


class CategoryBreakdown(BaseModel):
    category_id: int | None
    category_name: str
    entradas_cents: int
    saidas_cents: int
    saldo_cents: int
    qtd_transacoes: int


class SummaryResponse(BaseModel):
    company_id: int
    period: Period
    totals: Totals
    by_category: list[CategoryBreakdown]


class DailyPoint(BaseModel):
    date: str = Field(description="YYYY-MM-DD")
    entradas_cents: int
    saidas_cents: int
    saldo_cents: int


class DailyResponse(BaseModel):
    company_id: int
    period: Period
    series: list[DailyPoint]


class TransactionBrief(BaseModel):
    id: int
    occurred_at: datetime | None
    kind: str
    amount_cents: int
    category_id: int | None
    category_name: str
    description: str


class ContextResponse(BaseModel):
    company_id: int
    period: Period
    totals: Totals
    by_category: list[CategoryBreakdown]
    recent_transactions: list[TransactionBrief]


class TopCategoriesResponse(BaseModel):
    company_id: int
    period: Period
    metric: str
    items: list[CategoryBreakdown]
