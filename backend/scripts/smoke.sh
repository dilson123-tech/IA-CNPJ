#!/usr/bin/env bash
set -euo pipefail

BASE="${BASE:-http://127.0.0.1:8100}"

# autodetect prefix (/api/v1) via OpenAPI (compat)
API_PREFIX="${API_PREFIX:-}"
if [ -z "${API_PREFIX}" ]; then
  oa="$(curl -sS --max-time 6 "${BASE}/openapi.json" || true)"
  if echo "$oa" | grep -q '"/api/v1/ai/consult"'; then
    API_PREFIX="/api/v1"
  else
    API_PREFIX=""
  fi
fi
echo "[smoke] API_PREFIX=$API_PREFIX"
COMPANY_ID="${COMPANY_ID:-1}"
START="${START:-2026-01-01}"
END="${END:-2026-01-31}"
LIMIT="${LIMIT:-5}"

TOTAL=11
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


  step 8 "/ai/suggest-categories"
  curl -sS --max-time 8 -H 'Content-Type: application/json' \
    -d "{\"company_id\":$COMPANY_ID,\"start\":\"$START\",\"end\":\"$END\",\"limit\":50,\"include_no_match\":true}" \
    "$BASE/ai/suggest-categories" | jq -e . >/dev/null
  echo "OK"

  step 9 "/ai/apply-suggestions (dry-run)"
  curl -sS --max-time 10 -H 'Content-Type: application/json' \
    -d "{\"company_id\":$COMPANY_ID,\"start\":\"$START\",\"end\":\"$END\",\"limit\":200,\"dry_run\":true,\"include_no_match\":true}" \
    "$BASE/ai/apply-suggestions" | jq -e . >/dev/null
  echo "OK"

  step 10 "/ai/apply-suggestions (apply)"
  curl -sS --max-time 10 -H 'Content-Type: application/json' \
    -d "{\"company_id\":$COMPANY_ID,\"start\":\"$START\",\"end\":\"$END\",\"limit\":200,\"dry_run\":false}" \
    "$BASE/ai/apply-suggestions" | jq -e . >/dev/null
  echo "OK"


step 11 "/ai/consult"


# contrato mínimo do /ai/consult (não quebra cliente)
echo
echo "[contract] /ai/consult shape + caps"

tmp="/tmp/ai_consult_contract.json"
code="$(curl -sS --max-time 6 -o "$tmp" -w '%{http_code}' "$BASE/ai/consult" \
  -H 'Content-Type: application/json' \
  -d "{\"company_id\":$COMPANY_ID,\"start\":\"$START\",\"end\":\"$END\",\"limit\":20,\"question\":\"onde estou gastando mais?\"}")"

if [ "$code" != "200" ]; then
  echo "❌ /ai/consult HTTP $code"
  echo "---- body ----"
  cat "$tmp" || true
  echo "--------------"
  exit 1
fi

jq -e '
  (.company_id|type=="number") and
  (.period|type=="object") and
  (.period.start|type=="string") and
  (.period.end|type=="string") and
  (.headline|type=="string") and
  (.insights|type=="array") and
  (.risks|type=="array") and
  (.actions|type=="array") and
  (.top_categories|type=="array") and
  (.recent_transactions|type=="array") and
  ((.top_categories|length) <= 8) and
  ((.recent_transactions|length) <= 20)
' "$tmp" >/dev/null || {
  echo "❌ /ai/consult fora do contrato (dump abaixo)"
  cat "$tmp" | jq . || cat "$tmp"
  exit 1
}

echo "OK"

curl -sS --max-time 6 -H 'Content-Type: application/json' \
  -d "{\"company_id\":$COMPANY_ID,\"start\":\"$START\",\"end\":\"$END\",\"limit\":10,\"question\":\"smoke\"}" \
  "$BASE/ai/consult" | jq -e . >/dev/null
echo "OK"

echo
echo "✅ SMOKE PASS"
