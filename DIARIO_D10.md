# IA-CNPJ — Diário D10 (2026-01-20)

## Estado final
- Branch: `main`
- Commit: `deb5680`
- Branch protection (main):
  - strict: true (branches up to date)
  - required checks: `lint`, `smoke`

## Entregas do dia
- ✅ Smoke idempotência corrigido: `test(smoke): fix bash -u vars in idempotence step` (ficou verde).
- ✅ `gh pr checks` voltou a mostrar checks (login do `gh` resolvido).
- ✅ Proteção do `main` configurada (PR obrigatório + checks + up-to-date + sem bypass).
- ✅ PR #8 (`lab/d05-data-quality`) mergeado via **squash** e branch deletada.
- ✅ Pós-merge validado: `backend/scripts/dev_up_smoke.sh` => **DEV UP + SMOKE PASS** no `main`.

## Causa raiz do bloqueio do merge
O `main` exigia contexts `CI / lint` e `CI / smoke`, mas os checks reais do PR eram `lint` e `smoke`.
Resultado: tudo parecia “verde”, porém o merge ficava **BLOCKED** com `base branch policy prohibits the merge`.

## Fix aplicado
Atualizamos o branch protection:
- `required_status_checks.contexts = ["lint","smoke"]`
- mantendo `strict=true`

## Evidências rápidas
- `gh pr view 8 --json mergeStateStatus,mergeable` => `MERGEABLE` + `BLOCKED` (antes do fix)
- `gh pr view 8 --json statusCheckRollup` => `lint SUCCESS`, `smoke SUCCESS`
- `gh api .../required_status_checks` => `strict=true`, `contexts=["lint","smoke"]`
- Smoke local => **DEV UP + SMOKE PASS**

## Próximos passos (D11)
- Garantir que o workflow continue emitindo checks com nome `lint` e `smoke`.
- Se quiser voltar ao padrão “CI / lint” e “CI / smoke”, renomear jobs no `.github/workflows/ci.yml` e ajustar a proteção junto (sempre alinhado, sem mismatch).
