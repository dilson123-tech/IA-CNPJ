from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from passlib.hash import pbkdf2_sha256
import jwt

from app.core.settings import settings
from app.deps import get_db
from app.tenant_context import set_tenant_on_session
import secrets

bearer = HTTPBearer(auto_error=False)


def hash_password(plain: str) -> str:
    return pbkdf2_sha256.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    if not hashed:
        return False

    # Hash (passlib) normalmente começa com '$'
    if isinstance(hashed, str) and hashed.startswith("$"):
        try:
            return pbkdf2_sha256.verify(plain, hashed)
        except Exception:
            return False

    # Dev/CI: senha em texto puro
    return secrets.compare_digest(str(plain), str(hashed))

def _secret() -> str:
    sec = getattr(settings, "AUTH_JWT_SECRET", "") or ""
    if bool(getattr(settings, "AUTH_ENABLED", False)) and len(sec) < 32:
        raise RuntimeError("SECURITY: AUTH_JWT_SECRET fraco (min 32 chars) quando AUTH_ENABLED=true")
    if not sec:
        raise RuntimeError("SECURITY: AUTH_JWT_SECRET vazio (obrigatório quando AUTH_ENABLED=true)")
    return sec


def create_access_token(sub: str, tenant_id: int | None = None) -> str:
    # token simples e estável (CI/DEV/PROD)
    import os

    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=int(getattr(settings, "AUTH_JWT_EXPIRES_MINUTES", 60)))
    payload = {
        "sub": sub,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }
    if tenant_id is not None:
        payload["tenant_id"] = int(tenant_id)

    secret = (
        os.getenv("IA_CNPJ_AUTH_JWT_SECRET")
        or os.getenv("AUTH_JWT_SECRET")
        or getattr(settings, "AUTH_JWT_SECRET", "")
    )
    if not secret:
        raise RuntimeError("AUTH_JWT_SECRET vazio")

    return jwt.encode(payload, secret, algorithm="HS256")

def decode_token(token: str) -> Dict[str, Any]:
    try:
        return jwt.decode(token, _secret(), algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="token expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="token inválido",
            headers={"WWW-Authenticate": "Bearer"},
        )


def require_auth(
    credentials=Depends(bearer),
    db: Session = Depends(get_db),
):
    # auth ON?
    import os
    from fastapi import HTTPException

    enabled_raw = (
        os.getenv("IA_CNPJ_AUTH_ENABLED")
        or os.getenv("AUTH_ENABLED")
        or str(getattr(settings, "AUTH_ENABLED", "false"))
    ).strip().lower()
    enabled = enabled_raw in ("1", "true", "yes", "on")

    if not enabled:
        raise HTTPException(status_code=400, detail="Auth disabled")

    if not credentials:
        raise HTTPException(status_code=401, detail="Missing token")

    token = getattr(credentials, "credentials", None) or ""
    secret = (
        os.getenv("IA_CNPJ_AUTH_JWT_SECRET")
        or os.getenv("AUTH_JWT_SECRET")
        or getattr(settings, "AUTH_JWT_SECRET", "")
    )
    try:
        claims = jwt.decode(token, secret, algorithms=["HS256"])
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

    sub = (claims.get("sub") or "").strip()
    tenant_id = claims.get("tenant_id", None)

    # Se tenant_id não veio no JWT, resolve via DB pelo sub (email)
    if tenant_id in (None, "", 0):
        try:
            from app.models.tenant import TenantMember
            m = db.query(TenantMember).filter(TenantMember.email == sub).first()
            if m:
                tenant_id = m.tenant_id
        except Exception:
            tenant_id = None

    if tenant_id in (None, "", 0):
        raise HTTPException(status_code=401, detail="Missing tenant_id")

    tenant_id = int(tenant_id)
    claims["tenant_id"] = tenant_id

    # seta tenant no contexto da sessão (Postgres RLS / SQLite info)
    set_tenant_on_session(db, tenant_id)
    return claims

