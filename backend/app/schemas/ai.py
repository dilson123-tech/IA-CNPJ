from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field

from app.schemas.reports import Period, Totals, CategoryBreakdown, TransactionBrief


class AiConsultRequest(BaseModel):
    company_id: int = Field(..., ge=1)
    start: str | None = Field(None, description="YYYY-MM-DD ou ISO datetime")
    end: str | None = Field(None, description="YYYY-MM-DD ou ISO datetime")
    limit: int = Field(20, ge=1, le=200)
    question: str | None = Field(None, description="Pergunta opcional do usuário")


class AiConsultResponse(BaseModel):
    company_id: int
    period: Period
    generated_at: datetime

    headline: str
    insights: list[str]
    risks: list[str]
    actions: list[str]

    numbers: Totals
    top_categories: list[CategoryBreakdown]
    recent_transactions: list[TransactionBrief]
