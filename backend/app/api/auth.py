import secrets
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.core.settings import settings
from app.auth.jwt import create_access_token, require_auth

try:
    from passlib.hash import pbkdf2_sha256
except Exception:
    pbkdf2_sha256 = None  # fallback


router = APIRouter(prefix="/auth", tags=["auth"])


class LoginIn(BaseModel):
    username: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


def _verify_password(pw: str) -> bool:
    # Prefer hash
    ph = str(getattr(settings, "AUTH_PASSWORD_HASH", "") or "").strip()
    if ph:
        if pbkdf2_sha256 is None:
            raise RuntimeError("SECURITY: AUTH_PASSWORD_HASH definido mas passlib não está disponível")
        return pbkdf2_sha256.verify(pw, ph)

    # Fallback: plaintext (ok pra lab; em prod prefira HASH)
    plain = str(getattr(settings, "AUTH_PASSWORD", "") or "")
    return secrets.compare_digest(pw, plain)


@router.post("/login", response_model=TokenOut)
def login(payload: LoginIn):
    if not bool(getattr(settings, "AUTH_ENABLED", False)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Auth disabled")

    user = str(getattr(settings, "AUTH_USERNAME", "") or "").strip()
    if not user:
        raise RuntimeError("SECURITY: AUTH_USERNAME obrigatório quando AUTH_ENABLED=true")

    if not secrets.compare_digest(payload.username.strip(), user):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if not _verify_password(payload.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    token = create_access_token(sub=user)
    return TokenOut(access_token=token)


@router.get("/me")
def me(claims=Depends(require_auth)):
    return {"sub": claims.get("sub"), "iat": claims.get("iat"), "exp": claims.get("exp")}
