from sqlalchemy import text
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.deps import get_db
from app.core.security import require_auth
from app.models.tenant import TenantMember


def get_current_tenant_id(
    payload: dict = Depends(require_auth),
    db: Session = Depends(get_db),
) -> int:
    """
    Resolve tenant_id real baseado no email (sub) do JWT.
    Em Postgres: SET app.tenant_id
    Em SQLite (lab): guarda em db.info["tenant_id"]
    """
    email = payload.get("sub")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="token inválido (sub ausente)",
        )

    member = (
        db.query(TenantMember)
        .filter(TenantMember.email == email)
        .first()
    )

    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="usuário não pertence a nenhum tenant",
        )

    dialect = db.get_bind().dialect.name
    if str(dialect).startswith("postgres"):
        db.execute(text("SET app.tenant_id = :tid"), {"tid": str(member.tenant_id)})
    else:
        db.info["tenant_id"] = member.tenant_id

    return member.tenant_id
