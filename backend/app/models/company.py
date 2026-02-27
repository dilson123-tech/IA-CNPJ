from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column
from app.db import Base

class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    cnpj: Mapped[str] = mapped_column(String(14), unique=True, index=True)
    razao_social: Mapped[str] = mapped_column(String(200))
    tenant_id: Mapped[int] = mapped_column(nullable=False, index=True)
