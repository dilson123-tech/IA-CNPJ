from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Any, Dict

from fastapi import HTTPException, Request, status

from app.core.settings import settings


_SECRET_CACHE: str | None = None


def _b64url_encode(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode("utf-8")


def _b64url_decode(s: str) -> bytes:
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode((s + pad).encode("utf-8"))


def _secret() -> str:
    global _SECRET_CACHE
    if _SECRET_CACHE:
        return _SECRET_CACHE

    sec = str(getattr(settings, "AUTH_JWT_SECRET", "") or "").strip()
    if not sec:
        if getattr(settings, "ENV", "lab") == "prod":
            raise RuntimeError("SECURITY: AUTH_JWT_SECRET obrigatório em ENV=prod")
        sec = secrets.token_urlsafe(48)

    _SECRET_CACHE = sec
    return sec


def create_access_token(sub: str) -> str:
    now = int(time.time())
    ttl_min = int(getattr(settings, "AUTH_JWT_TTL_MIN", 60) or 60)

    header = {"alg": "HS256", "typ": "JWT"}
    payload: Dict[str, Any] = {
        "sub": sub,
        "iat": now,
        "exp": now + ttl_min * 60,
    }

    h = _b64url_encode(json.dumps(header, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))
    p = _b64url_encode(json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))
    signing_input = f"{h}.{p}".encode("utf-8")

    sig = hmac.new(_secret().encode("utf-8"), signing_input, hashlib.sha256).digest()
    s = _b64url_encode(sig)
    return f"{h}.{p}.{s}"


def decode_token(token: str) -> Dict[str, Any]:
    try:
        h_b64, p_b64, s_b64 = token.split(".")
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    signing_input = f"{h_b64}.{p_b64}".encode("utf-8")
    expected = hmac.new(_secret().encode("utf-8"), signing_input, hashlib.sha256).digest()
    got = _b64url_decode(s_b64)

    if not hmac.compare_digest(expected, got):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    payload = json.loads(_b64url_decode(p_b64).decode("utf-8"))
    exp = int(payload.get("exp", 0) or 0)
    if exp and int(time.time()) >= exp:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")

    return payload


def require_auth(request: Request) -> Dict[str, Any]:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")

    token = auth.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")

    return decode_token(token)
