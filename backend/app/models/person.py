from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, UniqueConstraint, Index, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

from app.db import Base


class Person(Base):
    __tablename__ = "persons"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)

    cpf = Column(String(11), nullable=False)
    cpf_masked = Column(String(14), nullable=False)

    full_name = Column(String(255), nullable=True)
    birth_date = Column(String(10), nullable=True)

    is_valid_cpf = Column(Boolean, nullable=False, default=False)
    validation_status = Column(String(50), nullable=False, default="unchecked")

    source = Column(String(80), nullable=False, default="manual")
    consent_reference = Column(String(255), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("tenant_id", "cpf", name="uq_persons_tenant_cpf"),
        Index("ix_persons_tenant_cpf", "tenant_id", "cpf"),
    )
