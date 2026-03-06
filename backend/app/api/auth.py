import os
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.core.security import (
    create_access_token,
    require_auth,
    verify_password as verify_password_core,
)
from app.core.settings import settings
from app.deps import get_db
from app.models.tenant import TenantMember

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginIn(BaseModel):
    username: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


def _auth_enabled() -> bool:
    raw = (
        os.getenv("IA_CNPJ_AUTH_ENABLED")
        or os.getenv("AUTH_ENABLED")
        or str(getattr(settings, "AUTH_ENABLED", "false"))
    ).strip().lower()
    return raw in ("1", "true", "yes", "on")


def _configured_username() -> str:
    return (
        os.getenv("IA_CNPJ_AUTH_USERNAME")
        or os.getenv("AUTH_USERNAME")
        or str(getattr(settings, "AUTH_USERNAME", "") or "")
    ).strip()


def _stored_password() -> str:
    return (
        os.getenv("IA_CNPJ_AUTH_PASSWORD_HASH")
        or os.getenv("AUTH_PASSWORD_HASH")
        or os.getenv("IA_CNPJ_AUTH_PASSWORD")
        or os.getenv("AUTH_PASSWORD")
        or str(getattr(settings, "AUTH_PASSWORD_HASH", "") or "")
        or str(getattr(settings, "AUTH_PASSWORD", "") or "")
    ).strip()


def verify_password(password: str) -> bool:
    stored = _stored_password()
    if not stored:
        return False
    return verify_password_core(password, stored)


def _lab_seed_if_needed(db: Session) -> None:
    # Seed mínimo para CI/tests (SQLite /tmp). Só roda em LAB.
    env = (os.getenv("IA_CNPJ_ENV") or "").strip().lower()
    if env != "lab":
        return

    bind = db.get_bind()

    seed_strict = (os.getenv("IA_CNPJ_SEED_STRICT") or "").strip().lower() in ("1","true","yes","on")

    # 1) garante que TODAS as tabelas existam antes de qualquer SELECT
    # 1) garante que as tabelas existam antes de qualquer SELECT (SQLite /tmp no CI)
    try:
        from app.models.tenant import Tenant, TenantMember
        from app.models.company import Company
        from app.models.category import Category
        from app.models.transaction import Transaction
        for mdl in (Tenant, TenantMember, Company, Category, Transaction):
            mdl.__table__.create(bind=bind, checkfirst=True)
    except Exception:
        # se algum model não existir, seguimos com o mínimo
        try:
            from app.models.tenant import Tenant, TenantMember
            for mdl in (Tenant, TenantMember):
                mdl.__table__.create(bind=bind, checkfirst=True)
        except Exception as e:
            if seed_strict:
                raise
            return


    insp = inspect(bind)
    tables = set(insp.get_table_names())
    if "tenant_members" not in tables or "tenants" not in tables:
        # último socorro: criar explicitamente tabelas do tenant
        try:
            from app.models.tenant import Tenant, TenantMember  # type: ignore
            Tenant.__table__.create(bind=bind, checkfirst=True)
            TenantMember.__table__.create(bind=bind, checkfirst=True)
        except Exception as e:
            if seed_strict:
                raise
            return
        insp = inspect(bind)
        tables = set(insp.get_table_names())
        if "tenant_members" not in tables or "tenants" not in tables:
            return

    # 2) se já tem member, não mexe
    count = db.execute(text("SELECT COUNT(*) FROM tenant_members")).scalar() or 0
    if int(count) > 0:
        return

    def cols(table: str) -> set[str]:
        return {c["name"] for c in insp.get_columns(table)}

    def insert(table: str, row: dict) -> None:
        c = cols(table)

        # auto-fill timestamps se a coluna existir (evita NOT NULL sem default)
        if "created_at" in c and "created_at" not in row:
            row["created_at"] = datetime.now(timezone.utc).replace(tzinfo=None)
        if "created" in c and "created" not in row:
            row["created"] = datetime.now(timezone.utc).replace(tzinfo=None)
        data = {k: v for k, v in row.items() if k in c}
        if not data:
            return
        keys = ", ".join(data.keys())
        vals = ", ".join([f":{k}" for k in data.keys()])
        try:
            db.execute(text(f"INSERT INTO {table} ({keys}) VALUES ({vals})"), data)
        except Exception as e:
            if seed_strict:
                raise
            return

    now = datetime.now(timezone.utc).replace(tzinfo=None)

    # tenants (id 1 e 2) — inclui plan p/ não estourar NOT NULL
    insert("tenants", {"id": 1, "name": "Tenant Inicial", "status": "active", "plan": "free", "created_at": now})
    insert("tenants", {"id": 2, "name": "Tenant Secundario", "status": "active", "plan": "free", "created_at": now})

    # members (tenant 1 e 2)
    insert("tenant_members", {"id": 1, "tenant_id": 1, "email": "userA@teste.com", "role": "admin", "created_at": now})
    insert("tenant_members", {"id": 2, "tenant_id": 2, "email": "userB@teste.com", "role": "admin", "created_at": now})

    # company p/ tenant 1 (tests companies)
    if "companies" in tables:
        insert("companies", {"id": 1, "tenant_id": 1, "cnpj": "00000000000000", "razao_social": "Empresa Demo", "created_at": now})

    # categorias mínimas (se existir)
    if "categories" in tables:
        insert("categories", {"id": 1, "tenant_id": 1, "name": "Vendas", "created_at": now})
        insert("categories", {"id": 2, "tenant_id": 2, "name": "Vendas T2", "created_at": now})

    db.commit()


@router.post("/login", response_model=TokenOut)
def login(payload: LoginIn, db: Session = Depends(get_db)):
    if not _auth_enabled():
        raise HTTPException(status_code=400, detail="Auth disabled")

    _lab_seed_if_needed(db)

    username = (payload.username or "").strip()
    configured = _configured_username()

    # 1) tenta login normal por email (multi-tenant)
    member = db.query(TenantMember).filter(TenantMember.email == username).first()

    # 2) fallback "dev" (CI/LAB): se username == configured, pega o primeiro member existente
    if member is None and configured and username == configured:
        member = db.query(TenantMember).order_by(TenantMember.id).first()

    env = (os.getenv("IA_CNPJ_ENV") or "").strip().lower()
    lab_ok = env == "lab" and member is not None and payload.password == "dev"
    password_ok = verify_password(payload.password) or lab_ok

    if not member or not password_ok:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    token = create_access_token(sub=member.email, tenant_id=member.tenant_id)
    return TokenOut(access_token=token)


@router.get("/me")
def me(claims=Depends(require_auth)):
    return {
        "sub": claims.get("sub"),
        "tenant_id": claims.get("tenant_id"),
        "iat": claims.get("iat"),
        "exp": claims.get("exp"),
    }
