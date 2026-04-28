from pydantic import BaseModel, Field
from typing import Literal, Optional


BillingType = Literal["PIX", "CREDIT_CARD"]


class CreateCheckoutRequest(BaseModel):
    package_code: str = Field(..., min_length=2, max_length=50)
    billing_type: BillingType
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    customer_cpf_cnpj: Optional[str] = None


class CreateCheckoutResponse(BaseModel):
    purchase_id: int
    package_code: str
    credits_amount: int
    amount_cents: int
    currency: str
    billing_type: str
    status: str
    provider: str
    payment_url: Optional[str] = None
    provider_reference: Optional[str] = None
    sandbox_message: Optional[str] = None


class PurchaseHistoryItem(BaseModel):
    purchase_id: int
    package_code: str
    credits_amount: int
    amount_cents: int
    currency: str
    billing_type: str
    status: str
    provider: str
    payment_url: Optional[str] = None
    provider_reference: Optional[str] = None
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    customer_cpf_cnpj: Optional[str] = None
    paid_at: Optional[str] = None
    created_at: Optional[str] = None
