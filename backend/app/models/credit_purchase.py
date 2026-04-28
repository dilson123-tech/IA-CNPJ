from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func

from app.db import Base


class CreditPurchase(Base):
    __tablename__ = "credit_purchases"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)

    package_code = Column(String(50), nullable=False)
    credits_amount = Column(Integer, nullable=False)
    amount_cents = Column(Integer, nullable=False)
    currency = Column(String(10), nullable=False, default="BRL")

    provider = Column(String(30), nullable=False, default="asaas")
    billing_type = Column(String(30), nullable=False)  # PIX | CREDIT_CARD | UNDEFINED
    status = Column(String(30), nullable=False, default="pending")  # pending | paid | failed | expired

    provider_reference = Column(String(120), nullable=True)
    payment_url = Column(String(500), nullable=True)

    customer_name = Column(String(255), nullable=True)
    customer_email = Column(String(255), nullable=True)
    customer_cpf_cnpj = Column(String(20), nullable=True)

    paid_at = Column(DateTime(timezone=True), nullable=True)
    credits_applied_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
