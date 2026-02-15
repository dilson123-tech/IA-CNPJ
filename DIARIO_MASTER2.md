# DIÁRIO MASTER2

## 2026-02-15 11:34 — Smoke estável + contracts + anti-leak guard + PDF hardening

- Corrigimos o smoke no CI que estava morrendo com `rc=139` (segfault) no bash; migramos preflight/health/json checks para Python (determinístico).
- Preflight `ensure company` agora usa fallback: tenta auth-aware e não trava com 401/token expirado.
- Contratos determinísticos adicionados:
  - `/ai/consult` shape + caps (limites de payload) ✅
  - `/reports/ai-consult/pdf`: valida HTTP 200 + `content-type=application/pdf` + magic `%PDF` ✅
- Anti-leak guard no CI: garante que **não vaza** `Authorization: Bearer` nem JWT (`eyJhbGci`) nos logs (inclui `/tmp/ci_smoke.log` e `/tmp/ci_api.log`).
- Seed/migration inclui categoria **Testes** (e regra `teste|testes|qa|homolog...`) e exportamos `RULES` para tests/contracts.
- PRs mergeadas:
  - #49 (ci(smoke): run scripts/smoke.sh in CI)
  - #51 (fix(ai): export RULES for tests/contracts)
  - #52 (test(smoke): harden pdf validation (size+peek+token-expired retry))

Status: CI main ✅ (workflow .github/workflows/ci.yml)

---

Master2 — Smoke estável (segfault-free + auth-aware + contract)
Corrigimos o smoke que estava morrendo com rc=139 (segfault) em bash/curl, migrando checks críticos para Python (health, req_json e preflight ensure_company). O smoke ficou “auth-aware”, com fallback em 401 e refresh em “Token expired”. Adicionamos contrato determinístico no /ai/consult (shape + caps) e mantivemos validação do PDF em /reports/ai-consult/pdf. CI agora sobe API via uvicorn e roda scripts/smoke.sh com anti-leak guard (sem vazar Authorization/JWT), passando 12/12 local e no GitHub Actions.
