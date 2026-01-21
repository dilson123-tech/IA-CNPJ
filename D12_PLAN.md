# D12 — IA Consultora CNPJ (modo produto real)

Objetivo: elevar o /ai/consult pra “consultor” com evidências auditáveis + observabilidade mínima, sem quebrar contrato e com gates (lint/smoke/openapi).

---

## Escopo (o que entra)

### 1) Consultor com evidências (auditável)
- **Sempre** retornar recomendações com **base objetiva**:
  - categoria/valor/percentual
  - **tx_ids** (referências) quando aplicável
  - janela de período (start/end)
- Gerar:
  - `headline` (1 frase)
  - `insights` (até 12)
  - `risks` (até 12)
  - `actions` (até 12)

### 2) Observabilidade mínima (produção-friendly)
- `request_id` por requisição (se já existir header, reaproveita; senão gera UUID)
- Log estruturado (json ou key=value) com:
  - request_id, company_id, start, end
  - duração_ms
  - counts: qtd_transacoes, qtd_sem_categoria, top_out_pct etc.
- Erros: retornar `error_code` consistente + logar stacktrace **somente no server**.

### 3) Contrato de API (compat e rastreável)
- Snapshot do OpenAPI (arquivo versionado) **ou** teste que valida campos do /ai/consult.
- Garantir que mudanças sejam “additive” (não quebra cliente).

---

## Fora de escopo (por enquanto)
- LLM real (OpenAI etc.). Aqui é determinístico + “plugável”.
- UI.
- Métricas Prometheus completas.

---

## DoD (Definition of Done) — gates
- `python -m py_compile` OK
- `bash -n scripts/dev_up_smoke.sh` OK
- `bash scripts/dev_up_smoke.sh` => **✅ DEV UP + SMOKE PASS**
- (Opcional mas recomendado) snapshot OpenAPI atualizado

---

## Plano de execução (micro-patches)

### Patch A — request_id + timing
- Criar helper leve em `app/api/ai.py`:
  - `request_id = header X-Request-ID ou uuid4()`
  - medir start/end e logar duração
- Não muda schema de resposta (se quiser incluir request_id no payload, só se schema permitir; senão log only).

### Patch B — evidências no consult
- Quando montar insights/risks/actions:
  - incluir percentuais e valores
  - puxar `recent_transactions` (já capado em 20) como evidência
  - se “sem categoria” relevante, recomendar /ai/suggest + /ai/apply com dry_run

### Patch C — contrato (teste)
Opção 1 (rápida):
- Adicionar no `scripts/smoke.sh` uma validação de forma do JSON do `/ai/consult` (jq):
  - existe `company_id`, `period.start`, `period.end`
  - arrays `insights/risks/actions` são arrays
  - `top_categories` máx 8
  - `recent_transactions` máx 20

Opção 2 (mais forte):
- salvar `openapi.json` (ou só o schema do `/ai/consult`) em `docs/contracts/openapi_ai_consult.json`
- smoke valida que o schema não sumiu (diff básico)

---

## Comandos (ordem padrão)
1) typecheck/compile:
   - `cd backend && python -m py_compile app/api/ai.py`
2) smoke:
   - `cd backend && bash scripts/dev_up_smoke.sh`

---

## Critérios de qualidade
- Nada de “texto fofo”: tudo tem número/percentual.
- “Sem categoria” vira alerta automaticamente se passar de ~10% do volume.
- Logs não vazam dados sensíveis (descrição pode ser truncada).

