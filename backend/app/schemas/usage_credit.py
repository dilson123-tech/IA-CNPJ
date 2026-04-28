from pydantic import BaseModel


class UsageCreditResponse(BaseModel):
    tenant_id: int
    balance: int
    consumed: int
    source: str

    class Config:
        from_attributes = True
