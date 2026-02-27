import secrets
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.settings import settings
from app.core.security import create_access_token, require_auth
from app.deps import get_db
from app.models.tenant import TenantMember

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginIn(BaseModel):
    username: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


def verify_password(pw: str) -> bool:
    # Simplificação temporária: senha global
    expected = str(getattr(settings, "AUTH_PASSWORD", "") or "")
    return secrets.compare_digest(pw, expected)


@router.post("/login", response_model=TokenOut)
def login(payload: LoginIn, db: Session = Depends(get_db)):
    if not bool(getattr(settings, "AUTH_ENABLED", False)):
        raise HTTPException(status_code=400, detail="Auth disabled")

    member = (
        db.query(TenantMember)
        .filter(TenantMember.email == payload.username.strip())
        .first()
    )

    if not member:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    if not verify_password(payload.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    token = create_access_token(sub=member.email)
    return TokenOut(access_token=token)


@router.get("/me")
def me(claims=Depends(require_auth)):
    return {
        "sub": claims.get("sub"),
        "iat": claims.get("iat"),
        "exp": claims.get("exp"),
    }
