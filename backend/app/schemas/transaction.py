from pydantic import BaseModel, ConfigDict
from datetime import datetime


class TransactionCreate(BaseModel):
    company_id: int
    kind: str
    amount_cents: int
    description: str | None = ""
    occurred_at: datetime | None = None
    category_id: int


class TransactionOut(BaseModel):
    id: int
    company_id: int
    kind: str
    amount_cents: int
    description: str
    occurred_at: datetime | None
    category_id: int

    model_config = ConfigDict(from_attributes=True)


class TransactionCategoryPatch(BaseModel):
    category_id: int

    model_config = ConfigDict(from_attributes=True)


class BulkCategorizeRequest(BaseModel):
    transaction_ids: list[int]
    category_id: int


class BulkCategorizeResponse(BaseModel):
    company_id: int
    updated: int
