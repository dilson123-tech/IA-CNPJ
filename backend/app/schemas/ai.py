from typing import Optional, List

from datetime import datetime
from pydantic import BaseModel, Field, AliasChoices, ConfigDict

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

class AIPeriod(BaseModel):
    start: str = Field(..., description="YYYY-MM-DD")
    end: str = Field(..., description="YYYY-MM-DD")


class AISuggestCategoriesRequest(BaseModel):
    """
    Compat: aceita start/end e também start_date/end_date (front).
    """
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


class AISuggestCategoriesResponse(BaseModel):
    company_id: int
    period: AIPeriod
    items: List[AISuggestedItem] = []

# -----------------------------
# D07: AI facade - apply suggestions (determinístico por enquanto)
# -----------------------------

from pydantic import BaseModel, Field

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
