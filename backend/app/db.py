from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.core.settings import settings
from app.utils.db_sequence_fix import fix_sequences

_is_sqlite = settings.DATABASE_URL.startswith("sqlite")

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if _is_sqlite else {},
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def get_admin_db():
    db = SessionLocal()
    try:
        fix_sequences(db, settings.DATABASE_URL)
        if not _is_sqlite:
            db.execute(text("SET row_security = off"))
            db.commit()
        yield db
    finally:
        db.close()

class Base(DeclarativeBase):
    pass



from sqlalchemy.orm import Session

# dependency padrão FastAPI
def get_db() -> "Session":
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
