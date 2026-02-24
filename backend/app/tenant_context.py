from sqlalchemy import text
from sqlalchemy.orm import Session

def set_tenant_on_session(db: Session, tenant_id: int) -> None:
    """
    Define o tenant_id na sessão ativa.

    - Postgres: SET app.tenant_id = <id> (para RLS / policies)
    - SQLite (lab): guarda em db.info["tenant_id"] para filtros em nível ORM
    """
    dialect = db.get_bind().dialect.name
    if str(dialect).startswith("postgres"):
        db.execute(text("SET app.tenant_id = :tid"), {"tid": str(tenant_id)})
    else:
        db.info["tenant_id"] = tenant_id
