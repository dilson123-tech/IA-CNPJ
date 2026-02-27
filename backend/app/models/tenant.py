from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db import Base


class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    plan = Column(String, default="basic", nullable=False)
    status = Column(String, default="trial", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    members = relationship("TenantMember", back_populates="tenant")


class TenantMember(Base):
    __tablename__ = "tenant_members"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    email = Column(String, nullable=False)
    role = Column(String, default="owner", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    tenant = relationship("Tenant", back_populates="members")
