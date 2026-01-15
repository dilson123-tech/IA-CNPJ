# IA-CNPJ (Consultoria Financeira com IA)

Produto robusto (comercial) focado em CNPJ/MEI: diagnóstico financeiro, alertas, relatórios e consultoria assistida por IA.
Este repositório é separado do Aurea Gold para manter estabilidade, compliance e evolução organizada.

## Estrutura
- backend/  -> API (FastAPI) + regras/serviços + integrações
- frontend/ -> Painel web (futuro: app)
- docs/     -> governança (roadmap, decisões, escopo)
- scripts/  -> automações de dev

## Regras (anti-bagunça)
1. Mudanças seguem o PDF Diário (8h). Ideias fora disso entram no Backlog.
2. Um comando por vez + testes determinísticos (curl) antes de UI.
3. LAB ≠ PROD. Nada quebra o estável.

## Data Quality (categorias)

> **Dica:** por padrão, o endpoint **não retorna** itens com `rule=no_match`.
> Para listar também os sem match (debug/triagem), use `include_no_match=true`.

### Listar transações sem categoria
```bash
curl -sS "http://127.0.0.1:8100/transactions/uncategorized?company_id=1&start=2026-01-01&end=2026-01-31&limit=50" | jq
```

### Setar categoria de uma transação (PATCH)
```bash
curl -sS -X PATCH "http://127.0.0.1:8100/transactions/3/category?company_id=1" \
  -H 'Content-Type: application/json' \
  -d '{"category_id":1}' | jq
```

### Categorizar em lote (bulk-categorize)
**Formato suportado:** `items: [{id, category_id}]`
```bash
curl -sS "http://127.0.0.1:8100/transactions/uncategorized?company_id=1&start=2026-01-01&end=2026-01-31&limit=200" \
| jq '{company_id: 1, items: map({id: .id, category_id: 1})}' \
| curl -sS -X POST "http://127.0.0.1:8100/transactions/bulk-categorize" \
  -H 'Content-Type: application/json' -d @- | jq
```

### Aplicar sugestões automaticamente (1 comando)
- Faz **dry-run** (mostra quantas seriam categorizadas)
- Depois **aplica** de verdade (atualiza no banco)

```bash
API="http://127.0.0.1:8100"

# dry-run (não altera nada)
curl -sS -X POST \
"$API/transactions/apply-suggestions?company_id=1&start=2026-01-01&end=2026-01-31&limit=200&dry_run=true" | jq

# apply (altera)
curl -sS -X POST \
"$API/transactions/apply-suggestions?company_id=1&start=2026-01-01&end=2026-01-31&limit=200" | jq
```

## Smoke tests (AI suggest/apply)

Esse teste garante que o fluxo **AI → sugerir categoria → aplicar categoria** está funcionando de ponta a ponta,
de forma **determinística** (valida pelo `TX_ID` criado no próprio smoke).

**Pré-requisitos**
- Backend rodando em `http://127.0.0.1:8100`
- `curl` e `jq` instalados

**Rodar**
```bash
cd backend
bash -n scripts/smoke_ai_apply.sh && echo "BASH OK ✅"
./scripts/smoke_ai_apply.sh
```

**O que valida**
- `/health` responde OK
- cria uma transação **sem categoria** com tag `__SMOKE_AI__...`
- `/ai/suggest-categories` retorna sugestão para aquele `TX_ID`
- `/ai/apply-suggestions` aplica e o `TX_ID` fica com `category_id` esperado

**Config via env (opcional)**
```bash
API=http://127.0.0.1:8100 COMPANY_ID=1 START=2026-01-01 END=2026-01-31 LIMIT=200 ./scripts/smoke_ai_apply.sh
```
- trigger CI checks for branch protection
