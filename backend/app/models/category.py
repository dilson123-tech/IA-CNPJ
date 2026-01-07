from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column
from app.db import Base

class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(80), unique=True, index=True)
