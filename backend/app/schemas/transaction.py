from datetime import datetime
from pydantic import BaseModel, Field

class TransactionCreate(BaseModel):
    company_id: int
    category_id: int
    kind: str = Field(pattern="^(in|out)$")
    amount_cents: int = Field(ge=1)
    occurred_at: datetime | None = None
    description: str = Field(default="", max_length=200)

class TransactionOut(BaseModel):
    id: int
    company_id: int
    category_id: int
    kind: str
    amount_cents: int
    occurred_at: datetime | None = None
    description: str

    class Config:
        from_attributes = True

class TransactionCategoryPatch(BaseModel):
    category_id: int | None = Field(default=None, description="Categoria (ou null para limpar)")

class BulkCategorizeItem(BaseModel):
    id: int
    category_id: int | None = Field(default=None)

class BulkCategorizeRequest(BaseModel):
    company_id: int
    items: list[BulkCategorizeItem] = Field(default_factory=list)

class BulkCategorizeResponse(BaseModel):
    company_id: int
    updated: int
    missing_ids: list[int] = Field(default_factory=list)
    skipped_ids: list[int] = Field(default_factory=list)
    invalid_category_ids: list[int] = Field(default_factory=list)
