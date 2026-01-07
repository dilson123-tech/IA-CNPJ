#!/usr/bin/env bash
set -euo pipefail

BASE="${BASE:-http://127.0.0.1:8100}"
COMPANY_ID="${COMPANY_ID:-1}"
START="${START:-2026-01-01}"
END="${END:-2026-01-31}"

echo "== IA-CNPJ SMOKE =="
echo "BASE=$BASE COMPANY_ID=$COMPANY_ID START=$START END=$END"
echo

echo "[1/3] /health"
curl -sS --max-time 4 "$BASE/health" | jq -e '.ok==true' >/dev/null
echo "OK"
echo

echo "[2/3] /reports/context"
curl -sS --max-time 6 "$BASE/reports/context?company_id=$COMPANY_ID&start=$START&end=$END&limit=5" \
| jq -e '.company_id==('"$COMPANY_ID"') and (.totals.qtd_transacoes>=0)' >/dev/null
echo "OK"
echo

echo "[3/4] /reports/top-categories
curl -sS --max-time 6 "$BASE/reports/top-categories?company_id=$COMPANY_ID&start=$START&end=$END&metric=saidas&limit=5" | jq -e . >/dev/null
echo "OK"

[4/4] /ai/consult"
curl -sS --max-time 6 -H 'Content-Type: application/json' \
  -d '{"company_id":'"$COMPANY_ID"',"start":"'"$START"'","end":"'"$END"'","limit":10,"question":"smoke"}' \
  "$BASE/ai/consult" \
| jq -e '.headline and (.numbers.qtd_transacoes>=0) and (.recent_transactions|type=="array")' >/dev/null
echo "OK"
echo

echo "✅ SMOKE PASS"
