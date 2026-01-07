from datetime import datetime
from pydantic import BaseModel, Field

class TransactionCreate(BaseModel):
    company_id: int
    category_id: int | None = None
    kind: str = Field(pattern="^(in|out)$")
    amount_cents: int = Field(ge=1)
    occurred_at: datetime | None = None
    description: str = Field(default="", max_length=200)

class TransactionOut(BaseModel):
    id: int
    company_id: int
    category_id: int | None
    kind: str
    amount_cents: int
    occurred_at: datetime | None = None
    description: str

    class Config:
        from_attributes = True
