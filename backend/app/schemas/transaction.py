from pydantic import BaseModel, Field

class TransactionCreate(BaseModel):
    company_id: int
    category_id: int | None = None
    kind: str = Field(pattern="^(in|out)$")
    amount_cents: int = Field(ge=1)
    description: str = Field(default="", max_length=200)

class TransactionOut(BaseModel):
    id: int
    company_id: int
    category_id: int | None
    kind: str
    amount_cents: int
    description: str

    class Config:
        from_attributes = True
