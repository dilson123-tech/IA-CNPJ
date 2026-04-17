from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.jwt import require_auth
from app.core.onboarding_admin import assert_onboarding_admin
from app.core.security import hash_password
from app.db import get_admin_db
from app.models.tenant import Tenant, TenantMember
from app.models.user import User

router = APIRouter(prefix="/admin/onboarding", tags=["admin-onboarding"])


class AdminProvisionIn(BaseModel):
    tenant_name: str
    email: str
    password: str
    plan: str = "basic"
    status: str = "trial"
    role: str = "owner"


@router.post("/clients")
def create_client(payload: AdminProvisionIn, db: Session = Depends(get_admin_db), claims=Depends(require_auth)):
    requester_email = (claims.get("sub") or "").strip().lower()
    assert_onboarding_admin(requester_email)

    email = (payload.email or "").strip().lower()
    tenant_name = (payload.tenant_name or "").strip()

    if not tenant_name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="tenant_name obrigatório")
    if not email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="email obrigatório")
    if not (payload.password or "").strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="password obrigatório")

    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Já existe user com este email")

    existing_member = db.query(TenantMember).filter(TenantMember.email == email).first()
    if existing_member:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Já existe tenant_member com este email")

    existing_tenant = db.query(Tenant).filter(Tenant.name == tenant_name).first()
    if existing_tenant:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Já existe tenant com este nome")

    tenant = Tenant(
        name=tenant_name,
        plan=(payload.plan or "basic").strip(),
        status=(payload.status or "trial").strip(),
    )
    db.add(tenant)
    db.flush()

    user = User(
        email=email,
        password_hash=hash_password(payload.password),
        is_active=True,
    )
    db.add(user)

    member = TenantMember(
        tenant_id=tenant.id,
        email=email,
        role=(payload.role or "owner").strip(),
    )
    db.add(member)

    db.commit()

    return {
        "ok": True,
        "tenant_id": tenant.id,
        "tenant_name": tenant.name,
        "user_email": user.email,
        "member_role": member.role,
    }
