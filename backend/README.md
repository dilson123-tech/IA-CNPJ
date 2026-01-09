# IA-CNPJ — Backend (FastAPI)

Backend do IA-CNPJ com trilha **Data Quality (rule-based)** + **IA Facade (provider switch)**.

## Rodar local

```bash
cd backend
. .venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8100 --reload


### OpenAI (provider real)

Ainda **desligado por padrão**. Quando implementarmos o provider real, ele vai ler:

```env
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_TIMEOUT_S=25
```

> Segurança: nunca commitar `.env` com chave real.
