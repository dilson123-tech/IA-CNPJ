# ROADMAP (MASTER v1)

## Código de Contexto (usar em TODO chat novo)
[PROJETO: IA-CNPJ]
[DOC: MASTER v1]
[DIA: 01]
[FOCO: Setup + estrutura + governança]
[STATUS: Em andamento]

## Objetivo do Produto
Consultoria financeira e fiscal assistida por IA para MEI/CNPJ:
- organização de entradas/saídas
- categorização
- alertas e riscos
- relatórios (mensal/semanal)
- orientação (sem substituir contador)

## Fases (macro)
Fase 0 - Setup e governança (Dia 01)
Fase 1 - Backend base (auth, contas, lançamentos, categorias)
Fase 2 - Painel web (login, dashboard, lançamentos, relatórios)
Fase 3 - IA Consultora (rotinas, prompts, guardrails)
Fase 4 - Fiscal/IR (orientação, checklist, relatórios)
Fase 5 - Produto comercial (planos, onboarding, métricas)

## Backlog (ideias fora do plano do dia)
- Integração Open Finance/CSV
- Exportação PDF/WhatsApp
- Multi-empresa (matriz/filiais)

## Checkpoints (stables)

### 2026-01-24 — Smoke DB-zerado proof ✅ (CI green)
Entregue: smoke “à prova de DB zerado” (seed/lookup por CNPJ), hardening fail-fast e documentação.

- PRs: #17 #18 #19
- Tags:
  - stable/2026-01-24-smoke-hardening
  - stable/2026-01-24-smoke-ai-ensure-company
  - stable/2026-01-24-readme-smoke
- Garantias:
  - smoke valida HTTP 2xx + JSON (fail-fast)
  - preflight ensure_company (seed/lookup por CNPJ)
  - bulk-categorize vira skip quando não há uncategorized
  - smoke_ai_apply valida fluxo AI suggest/apply + idempotência (re-apply dry_run=0)


### 2026-01-24 — CI Quality Gate ✅ (bash -n + shellcheck)
Entregue: quality gate no job `lint` para scripts bash (validação sintática + lint severo).

- PR: #21
- Tag:
  - stable/2026-01-24-quality-gate
- Garantias:
  - `bash -n` em `backend/scripts/*.sh`
  - `shellcheck -S error` (falha CI em warnings críticos)

### 2026-01-24 — Lint padronizado ✅ (ruff + make lint)
Entregue: padronização do lint local/CI com config do Ruff + alvo `make lint` (ruff + compileall + bash -n).

- PR: #23
- Tag:
  - stable/2026-01-24-ruff-make-lint
- Garantias:
  - Ruff configurado via `backend/pyproject.toml` (atual: `select=["F"]`)
  - `make lint` roda: ruff + `python -m compileall` + `bash -n` em `backend/scripts/*.sh`


### 2026-01-22 — Baseline smoke + contrato /ai/consult ✅
- Tags:
  - stable/2026-01-22-smoke
  - stable/2026-01-22

