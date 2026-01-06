from fastapi import FastAPI

app = FastAPI(title="IA-CNPJ API", version="0.1.0")

@app.get("/health")
def health():
    return {"ok": True, "service": "ia-cnpj", "version": "0.1.0"}
