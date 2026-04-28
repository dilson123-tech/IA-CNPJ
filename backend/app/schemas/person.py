from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID


class PersonCreate(BaseModel):
    cpf: str = Field(..., min_length=11, max_length=14)
    full_name: Optional[str] = None
    birth_date: Optional[str] = None
    consent_reference: Optional[str] = None


class PersonResponse(BaseModel):
    id: UUID
    cpf_masked: str
    full_name: Optional[str]
    birth_date: Optional[str]
    is_valid_cpf: bool
    validation_status: str
    source: str

    class Config:
        from_attributes = True
