# IA-CNPJ — Backend (FastAPI)

Backend do IA-CNPJ com trilha **Data Quality (rule-based)** + **IA Facade (provider switch)**.

## Rodar local

```bash
cd backend
. .venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8100 --reload

