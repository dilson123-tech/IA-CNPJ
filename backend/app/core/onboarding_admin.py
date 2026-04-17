from __future__ import annotations

from fastapi import HTTPException, status

from app.core.settings import settings


def get_onboarding_admin_emails() -> set[str]:
    raw = str(getattr(settings, "ONBOARDING_ADMIN_EMAILS", "") or "").strip()
    if not raw:
        return set()

    return {
        item.strip().lower()
        for item in raw.split(",")
        if item.strip()
    }


def assert_onboarding_admin(email: str) -> None:
    allowed = get_onboarding_admin_emails()
    normalized = (email or "").strip().lower()

    if not normalized or normalized not in allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden",
        )
