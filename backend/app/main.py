from fastapi import FastAPI
from app.core.settings import settings

# 🚫 Failsafe: em PROD, auth não pode estar desligado
if getattr(settings, "ENV", "dev") == "prod" and not bool(getattr(settings, "AUTH_ENABLED", False)):
    raise RuntimeError("SECURITY: ENV=prod requer AUTH_ENABLED=true (failsafe)")

from app.api.company import router as company_router
from app.api.category import router as category_router
from app.api.transaction import router as transaction_router
from app.api.reports import router as reports_router
from app.api.ai import router as ai_router

app = FastAPI(title=settings.APP_NAME, version="0.3.0")

app.include_router(company_router)
app.include_router(category_router)
app.include_router(transaction_router)
app.include_router(reports_router)
app.include_router(ai_router)

@app.get("/health")
def health():
    # health não pode quebrar nunca (nem em reload)
    auth_enabled = bool(getattr(settings, "AUTH_ENABLED", False))
    docs_protected = auth_enabled and (
        getattr(settings, "ENV", "dev") == "prod"
        or bool(getattr(settings, "AUTH_PROTECT_DOCS", False))
    )

    return {
        "ok": True,
        "service": "ia-cnpj",
        "env": getattr(settings, "ENV", "dev"),
        "version": "0.3.0",
        "auth_enabled": auth_enabled,
        "docs_protected": docs_protected,
    }


