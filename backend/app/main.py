from fastapi import FastAPI
from app.core.settings import settings
from app.api.company import router as company_router

app = FastAPI(title=settings.APP_NAME, version="0.2.0")
app.include_router(company_router)

@app.get("/health")
def health():
    return {"ok": True, "service": "ia-cnpj", "env": settings.ENV, "version": "0.2.0"}
