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

