from sqlalchemy import String, Integer, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.db import Base
from datetime import datetime

class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), nullable=False)

    # "in" (entrada) ou "out" (saida)
    kind: Mapped[str] = mapped_column(String(3), index=True)

    # valor em centavos (evita float)
    amount_cents: Mapped[int] = mapped_column(Integer)

    # data/hora do lançamento (base para relatórios)
    occurred_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)

    description: Mapped[str] = mapped_column(String(200), default="")
    tenant_id: Mapped[int] = mapped_column(nullable=False, index=True)
