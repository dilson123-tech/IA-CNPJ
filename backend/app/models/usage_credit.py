from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func

from app.db import Base


class TenantUsageCredit(Base):
    __tablename__ = "tenant_usage_credits"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    balance = Column(Integer, nullable=False, default=0)
    consumed = Column(Integer, nullable=False, default=0)
    source = Column(String(80), nullable=False, default="manual")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("tenant_id", name="uq_tenant_usage_credits_tenant_id"),
    )
