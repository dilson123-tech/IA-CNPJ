from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from passlib.hash import pbkdf2_sha256
import jwt

from app.core.settings import settings

bearer = HTTPBearer(auto_error=False)

def hash_password(plain: str) -> str:
    return pbkdf2_sha256.hash(plain)

def verify_password(plain: str, hashed: str) -> bool:
    if not hashed:
        return False
    return pbkdf2_sha256.verify(plain, hashed)

def _secret() -> str:
    sec = getattr(settings, "AUTH_JWT_SECRET", "") or ""
    if bool(getattr(settings, "AUTH_ENABLED", False)) and len(sec) < 32:
        raise RuntimeError("SECURITY: AUTH_JWT_SECRET fraco (min 32 chars) quando AUTH_ENABLED=true")
    if not sec:
        raise RuntimeError("SECURITY: AUTH_JWT_SECRET vazio (obrigatório quando AUTH_ENABLED=true)")
    return sec

def create_access_token(sub: str, ttl_s: int | None = None) -> str:
    ttl = int(ttl_s or getattr(settings, "AUTH_ACCESS_TOKEN_TTL_S", 3600))
    now = datetime.now(timezone.utc)
    payload: Dict[str, Any] = {
        "sub": sub,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=ttl)).timestamp()),
    }
    return jwt.encode(payload, _secret(), algorithm="HS256")

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

def require_auth(creds: HTTPAuthorizationCredentials = Depends(bearer)) -> Dict[str, Any]:
    if not creds or (creds.scheme or "").lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="não autenticado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return decode_token(creds.credentials)
