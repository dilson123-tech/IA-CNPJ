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
    consent_reference: Optional[str] = None

    document_type: str = "CPF"
    normalized_document: Optional[str] = None
    validation_status_label: Optional[str] = None
    risk_level: Optional[str] = None
    commercial_summary: Optional[str] = None
    recommended_action: Optional[str] = None
    lgpd_scope: Optional[str] = None
    bureau_required: bool = True
    bureau_note: Optional[str] = None
    checked_at: Optional[str] = None

    class Config:
        from_attributes = True
