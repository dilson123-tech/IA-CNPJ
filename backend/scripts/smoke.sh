#!/usr/bin/env bash
set -euo pipefail

BASE="${BASE:-http://127.0.0.1:8100}"
COMPANY_ID="${COMPANY_ID:-1}"
START="${START:-2026-01-01}"
END="${END:-2026-01-31}"
LIMIT="${LIMIT:-5}"

TOTAL=8
step(){ echo; echo "[$1/$TOTAL] $2"; }

echo "== IA-CNPJ SMOKE =="
echo "BASE=$BASE COMPANY_ID=$COMPANY_ID START=$START END=$END"

step 1 "/health"
curl -sS --max-time 4 "$BASE/health" | jq -e . >/dev/null
echo "OK"

step 2 "/reports/context"
curl -sS --max-time 6 "$BASE/reports/context?company_id=$COMPANY_ID&start=$START&end=$END&limit=$LIMIT" | jq -e . >/dev/null
echo "OK"

step 3 "/reports/top-categories"
curl -sS --max-time 6 "$BASE/reports/top-categories?company_id=$COMPANY_ID&start=$START&end=$END&metric=saidas&limit=5" | jq -e . >/dev/null
echo "OK"

step 4 "/transactions/uncategorized"
curl -sS --max-time 6 "$BASE/transactions/uncategorized?company_id=$COMPANY_ID&start=$START&end=$END&limit=50" | jq -e . >/dev/null
echo "OK"

step 5 "/transactions/bulk-categorize"
# pega uncategorized e monta payload items -> seta categoria 1
PAYLOAD="$(curl -sS --max-time 6 "$BASE/transactions/uncategorized?company_id=$COMPANY_ID&start=$START&end=$END&limit=200" \
| jq -c '{company_id: '"$COMPANY_ID"', items: map({id: .id, category_id: 1})}')"
curl -sS --max-time 10 -X POST "$BASE/transactions/bulk-categorize" \
  -H 'Content-Type: application/json' -d "$PAYLOAD" | jq -e . >/dev/null
echo "OK"


step 6 "/transactions/apply-suggestions (dry-run)"
curl -sS --max-time 8 -X POST   "$BASE/transactions/apply-suggestions?company_id=$COMPANY_ID&start=$START&end=$END&limit=200&dry_run=true" | jq -e . >/dev/null
echo "OK"

step 7 "/transactions/apply-suggestions (apply)"
curl -sS --max-time 8 -X POST   "$BASE/transactions/apply-suggestions?company_id=$COMPANY_ID&start=$START&end=$END&limit=200" | jq -e . >/dev/null
echo "OK"

step 8 "/ai/consult"
curl -sS --max-time 6 -H 'Content-Type: application/json' \
  -d "{\"company_id\":$COMPANY_ID,\"start\":\"$START\",\"end\":\"$END\",\"limit\":10,\"question\":\"smoke\"}" \
  "$BASE/ai/consult" | jq -e . >/dev/null
echo "OK"

echo
echo "✅ SMOKE PASS"
