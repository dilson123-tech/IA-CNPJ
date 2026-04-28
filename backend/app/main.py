from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
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
from app.api.admin_onboarding import router as admin_onboarding_router
from app.api.persons import router as persons_router
from app.api.usage_credits import router as usage_credits_router
from app.api.billing import router as billing_router, public_router as billing_public_router


# 🚫 Failsafe: em PROD, auth não pode estar desligado
if bool(getattr(settings, "AUTH_PROTECT_DOCS", False)) and not bool(getattr(settings, "AUTH_ENABLED", False)):
    raise RuntimeError("SECURITY: AUTH_PROTECT_DOCS requer AUTH_ENABLED=true")

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
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:4173",
        "http://localhost:4173",
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:5174",
        "http://localhost:5174",
        "https://ia-cnpj.vercel.app",
    ],
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(auth_router, prefix="/api/v1")

# Routers protegidos quando AUTH_ENABLED=true
app.include_router(company_router, dependencies=PROTECTED_DEPS)
app.include_router(company_router, prefix="/api/v1", dependencies=PROTECTED_DEPS)
app.include_router(category_router, dependencies=PROTECTED_DEPS)
app.include_router(category_router, prefix="/api/v1", dependencies=PROTECTED_DEPS)
app.include_router(transaction_router, dependencies=PROTECTED_DEPS)
app.include_router(transaction_router, prefix="/api/v1", dependencies=PROTECTED_DEPS)
app.include_router(reports_router, dependencies=PROTECTED_DEPS)
app.include_router(reports_router, prefix="/api/v1", dependencies=PROTECTED_DEPS)
app.include_router(ai_router, dependencies=PROTECTED_DEPS)
app.include_router(ai_router, prefix="/api/v1", dependencies=PROTECTED_DEPS)
app.include_router(admin_onboarding_router, dependencies=PROTECTED_DEPS)
app.include_router(admin_onboarding_router, prefix="/api/v1", dependencies=PROTECTED_DEPS)

app.include_router(persons_router, dependencies=PROTECTED_DEPS)
app.include_router(persons_router, prefix="/api/v1", dependencies=PROTECTED_DEPS)

app.include_router(usage_credits_router, dependencies=PROTECTED_DEPS)
app.include_router(usage_credits_router, prefix="/api/v1", dependencies=PROTECTED_DEPS)

app.include_router(billing_router, dependencies=PROTECTED_DEPS)
app.include_router(billing_router, prefix="/api/v1", dependencies=PROTECTED_DEPS)
app.include_router(billing_public_router)
app.include_router(billing_public_router, prefix="/api/v1")


@app.get("/health")
def health():
    return {
        "ok": True,
        "service": "ia-cnpj",
        "env": settings.ENV,
        "version": "0.3.0",
        "auth_enabled": bool(getattr(settings, "AUTH_ENABLED", False)),
        "auth_protect_docs": bool(getattr(settings, "AUTH_PROTECT_DOCS", False)),
        "build_sha": getattr(settings, "BUILD_SHA", ""),
        "docs_protected": bool(DOCS_PROTECTED),
    }


# 📚 Docs/OpenAPI: sempre existem; quando DOCS_PROTECTED=true exigem JWT
@app.get("/openapi.json", include_in_schema=False, dependencies=DOC_DEPS)
def openapi_json():
    schema = get_openapi(title=app.title, version=app.version, routes=app.routes)

    # --- OpenAPI hardening: expor Bearer JWT como security scheme ---
    comps = schema.setdefault('components', {})
    schemes = comps.setdefault('securitySchemes', {})
    schemes.setdefault('bearerAuth', {
        'type': 'http',
        'scheme': 'bearer',
        'bearerFormat': 'JWT',
    })

    # Rotas públicas: não exigem token (no schema)
    public_paths = {'/auth/login', '/health'}

    # Aplica security no schema para operações protegidas
    for path, ops in (schema.get('paths') or {}).items():
        if path in public_paths:
            continue
        for method, op in (ops or {}).items():
            if not isinstance(op, dict):
                continue
            # Não sobrescreve se já existir
            op.setdefault('security', [{'bearerAuth': []}])

    return JSONResponse(schema)


@app.get("/docs", include_in_schema=False, dependencies=DOC_DEPS)
def swagger_docs():
    return get_swagger_ui_html(openapi_url="/openapi.json", title=f"{app.title} - Docs")


@app.get("/redoc", include_in_schema=False, dependencies=DOC_DEPS)
def redoc_docs():
    return get_redoc_html(openapi_url="/openapi.json", title=f"{app.title} - ReDoc")
