from fastapi import Depends, FastAPI
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse

from app.core.settings import settings
from app.auth.jwt import require_auth

from app.api.auth import router as auth_router
from app.api.company import router as company_router
from app.api.category import router as category_router
from app.api.transaction import router as transaction_router
from app.api.reports import router as reports_router
from app.api.ai import router as ai_router


# 🚫 Failsafe: em PROD, auth não pode estar desligado
if getattr(settings, "ENV", "lab") == "prod" and not bool(getattr(settings, "AUTH_ENABLED", False)):
    raise RuntimeError("SECURITY: ENV=prod requer AUTH_ENABLED=true (failsafe)")

DOCS_PROTECTED = bool(getattr(settings, "AUTH_ENABLED", False)) and (
    getattr(settings, "ENV", "lab") == "prod" or bool(getattr(settings, "AUTH_PROTECT_DOCS", False))
)

DOC_DEPS = [Depends(require_auth)] if DOCS_PROTECTED else []
PROTECTED_DEPS = [Depends(require_auth)] if bool(getattr(settings, "AUTH_ENABLED", False)) else []

app = FastAPI(
    title=settings.APP_NAME,
    version="0.3.0",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

# Auth router sempre exposto (login precisa existir)
app.include_router(auth_router)

# Routers protegidos quando AUTH_ENABLED=true
app.include_router(company_router, dependencies=PROTECTED_DEPS)
app.include_router(category_router, dependencies=PROTECTED_DEPS)
app.include_router(transaction_router, dependencies=PROTECTED_DEPS)
app.include_router(reports_router, dependencies=PROTECTED_DEPS)
app.include_router(ai_router, dependencies=PROTECTED_DEPS)


@app.get("/health")
def health():
    return {
        "ok": True,
        "service": "ia-cnpj",
        "env": settings.ENV,
        "version": "0.3.0",
        "auth_enabled": bool(getattr(settings, "AUTH_ENABLED", False)),
        "docs_protected": bool(DOCS_PROTECTED),
    }


# 📚 Docs/OpenAPI: sempre existem; quando DOCS_PROTECTED=true exigem JWT
@app.get("/openapi.json", include_in_schema=False, dependencies=DOC_DEPS)
def openapi_json():
    schema = get_openapi(title=app.title, version=app.version, routes=app.routes)
    return JSONResponse(schema)


@app.get("/docs", include_in_schema=False, dependencies=DOC_DEPS)
def swagger_docs():
    return get_swagger_ui_html(openapi_url="/openapi.json", title=f"{app.title} - Docs")


@app.get("/redoc", include_in_schema=False, dependencies=DOC_DEPS)
def redoc_docs():
    return get_redoc_html(openapi_url="/openapi.json", title=f"{app.title} - ReDoc")
