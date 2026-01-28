from fastapi import FastAPI, Depends
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse

from app.core.settings import settings
from app.core.security import require_auth

from app.api.auth import router as auth_router
from app.api.company import router as company_router
from app.api.category import router as category_router
from app.api.transaction import router as transaction_router
from app.api.reports import router as reports_router
from app.api.ai import router as ai_router


# ✅ Proteção global (routers) quando AUTH_ENABLED=true
PROTECTED_DEPS = [Depends(require_auth)] if bool(getattr(settings, "AUTH_ENABLED", False)) else []

# ✅ Docs sempre existem; em PROD podem ser protegidos por JWT
PROTECT_DOCS = bool(getattr(settings, "AUTH_ENABLED", False)) and (
    getattr(settings, "ENV", "dev") == "prod" or bool(getattr(settings, "AUTH_PROTECT_DOCS", False))
)

# Dependências aplicadas nas rotas de docs/openapi
DOC_DEPS = PROTECTED_DEPS if PROTECT_DOCS else []


app = FastAPI(
    title=settings.APP_NAME,
    version="0.3.0",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

# Routers
app.include_router(auth_router)
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
        "env": getattr(settings, "ENV", "dev"),
        "version": "0.3.0",
    }


# 📚 Docs/OpenAPI: sempre existem; no PROD ficam protegidos por JWT
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
