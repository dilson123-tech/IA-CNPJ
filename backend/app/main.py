from fastapi import FastAPI
from app.core.settings import settings

from app.api.company import router as company_router
from app.api.category import router as category_router
from app.api.transaction import router as transaction_router
from app.api.reports import router as reports_router

app = FastAPI(title=settings.APP_NAME, version="0.3.0")

app.include_router(company_router)
app.include_router(category_router)
app.include_router(transaction_router)
app.include_router(reports_router)

@app.get("/health")
def health():
    return {
        "ok": True,
        "service": "ia-cnpj",
        "env": settings.ENV,
        "version": "0.3.0",
    }
