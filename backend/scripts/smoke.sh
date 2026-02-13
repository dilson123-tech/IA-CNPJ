#!/usr/bin/env bash
# SMOKE_FORCE_NO_XTRACE: evita herdar xtrace do runner (e evita leak / crash raro)
SMOKE_FORCE_NO_XTRACE=1
set +x
curl_auth() {
  local rc=0
  local _was_x=0
  case "$-" in *x*) _was_x=1; set +x ;; esac

  command curl "${CURL_AUTH[@]}" "$@" || rc=$?

  # workaround hard: curl segfault (rc=139) em runner -> fallback python para GET simples
  if (( rc == 139 )); then
    local has_body=0 has_method=0 a
    for a in "$@"; do
      case "$a" in
        -d|--data|--data-raw|--data-binary|--data-urlencode|-F|--form) has_body=1 ;;
        -X|--request) has_method=1 ;;
      esac
    done
    if (( has_body==0 && has_method==0 )); then
      local url="${@: -1}"
      rc=0
      python - "$url" <<'PYF'
import sys, urllib.request
url = sys.argv[1]
req = urllib.request.Request(url, method="GET")
try:
    with urllib.request.urlopen(req, timeout=15) as r:
        sys.stdout.buffer.write(r.read())
except Exception as e:
    sys.stderr.write(f"[curl_auth py fallback] error: {e}\n")
    sys.exit(7)
PYF
      rc=$?
    fi
  fi

  if (( rc != 0 )); then
    local url="${@: -1}"
    echo "[curl_auth] rc=$rc url=$url" >&2
  fi

  (( _was_x )) && set -x
  return $rc
}


set -euo pipefail

# === CI bootstrap: curl_auth SEMPRE existe antes de usar (e não vaza token sob xtrace) ===
declare -a CURL_AUTH=()
curl_auth() {
  local rc=0 _was_x=0
  [[ $- == *x* ]] && _was_x=1
  (( _was_x )) && set +x
  command curl "${CURL_AUTH[@]}" "$@" || rc=$?
  (( _was_x )) && set -x
  return $rc
}
# força TODAS as chamadas 'curl' passarem pelo wrapper (exceto quando usar 'command curl')
curl() { curl_auth "$@"; }


# === AUTH SMOKE AUTO-TOKEN ===
CURL_AUTH=()
CURL_AUTH_KEEP=()

restore_auth() {
  # guarda o primeiro header válido e restaura se alguém zerar CURL_AUTH
  if [[ ${#CURL_AUTH_KEEP[@]} -eq 0 ]] && [[ ${#CURL_AUTH[@]} -gt 0 ]]; then
    CURL_AUTH_KEEP=("${CURL_AUTH[@]}")
  fi
  if [[ "${_auth_enabled:-}" == "true" ]] && [[ ${#CURL_AUTH[@]} -eq 0 ]] && [[ ${#CURL_AUTH_KEEP[@]} -gt 0 ]]; then
    CURL_AUTH=("${CURL_AUTH_KEEP[@]}")
  fi
}
# wrap curl_auth: usa 'command curl' e anexa Authorization quando CURL_AUTH estiver setado
# 🔒 xtrace guard: se estiver em 'bash -x', desliga xtrace só durante o curl_auth real (não vaza token)
curl_auth() {
  local _was_x=0
  [[ $- == *x* ]] && _was_x=1
  ((_was_x)) && set +x
  local rc=0
  curl_auth "${CURL_AUTH[@]}" "$@" || rc=$?
  ((_was_x)) && set -x
  return $rc
}

BASE="${BASE:-http://127.0.0.1:8100}"

# auto-token quando AUTH estiver ligado (via /health)
_BASE="${BASE_URL:-${BASE:-http://127.0.0.1:8100}}"
_http="$(command curl -sS -o /dev/null -w "%{http_code}" --connect-timeout 1 --max-time 10 "$_BASE/health" 2>/dev/null || true)"
echo "[health] http=${_http:-none}"
if [[ "${_http:0:1}" == "2" || "${_http:0:1}" == "3" ]]; then
  _health="OK"
else
  _health=""
fi
if command -v jq >/dev/null 2>&1; then
  _auth_enabled="$(printf '%s' "$_health" | jq -er '.auth_enabled // false' 2>/dev/null || true)"
  if [[ -z "${_auth_enabled:-}" ]]; then
    _auth_enabled="$(printf '%s' "$_health" | sed -n 's/.*"auth_enabled"[[:space:]]*:[[:space:]]*\([^,}]*\).*/\1/p')"
  fi
else
  _auth_enabled="$(printf '%s' "$_health" | sed -n 's/.*"auth_enabled"[[:space:]]*:[[:space:]]*\([^,}]*\).*/\1/p')"
fi

if [[ "$_auth_enabled" == "true" ]]; then
  _user="${SMOKE_AUTH_USER:-${AUTH_USERNAME:-}}"
  _pass="${SMOKE_AUTH_PASS:-${AUTH_PASSWORD:-${AUTH_PLAIN_PASSWORD:-}}}"

  if [[ -n "${SMOKE_BEARER_TOKEN:-}" ]]; then
    _tok="${SMOKE_BEARER_TOKEN}"
  else
    if [[ -z "$_user" || -z "$_pass" ]]; then
      echo "❌ AUTH ativo, mas faltou credencial para smoke."
      echo "   Use: SMOKE_AUTH_USER=admin SMOKE_AUTH_PASS='SENHA' ./scripts/smoke.sh"
      exit 1
    fi

    _smoke_xtrace=0
    if [[ $- == *x* ]]; then _smoke_xtrace=1; set +x; fi
    _resp_file="${TMPDIR:-/tmp}/ia-cnpj__resp_$$.out"
    curl_auth -sS --max-time 5 "$_BASE/auth/login" \
      -H 'Content-Type: application/json' \
      -d "{\"username\":\"${_user}\",\"password\":\"${_pass}\"}" >"${_resp_file}"
    _resp=""  # não carregar payload em variável (evita rc=139)

    if command -v jq >/dev/null 2>&1; then
      _tok="$(printf '%s' "$_resp" | jq -er '.access_token // empty' 2>/dev/null || true)"
    if [[ -z "${_tok:-}" ]]; then
      _tok="$(printf '%s' "$_resp" | sed -n 's/.*"access_token"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')"
    fi
    else
      _tok="$(printf '%s' "$_resp" | sed -n 's/.*"access_token"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')"
    fi
  fi

  if [[ -z "${_tok:-}" || "${_tok:-}" == "null" ]]; then
    echo "❌ falhou pegar access_token do /auth/login"
    exit 1
  fi

  __x=0

  [[ $- == *x* ]] && __x=1 && set +x

  __hdr=/tmp/ia_cnpj_auth_header

  printf 'Authorization: Bearer %s' "${_tok}" > "$__hdr"

  CURL_AUTH=(-H "@$__hdr")

  ((__x==1)) && set -x

    if [[ $_smoke_xtrace -eq 1 ]]; then set -x; fi
  echo "[smoke] auth_enabled=true (token ok)"
else
  echo "[smoke] auth_enabled=false"
fi

# autodetect prefix (/api/v1) via OpenAPI (compat)
API_PREFIX="${API_PREFIX:-}"
if [ -z "$API_PREFIX" ]; then
oa_file="${TMPDIR:-/tmp}/ia-cnpj_openapi_$$.json"
curl_auth -sS --connect-timeout 1 --max-time 15 "$_BASE/openapi.json" >"$oa_file"
  if echo "$oa" | jq -e '.paths["/api/v1/ai/consult"]' >/dev/null 2>&1; then
    API_PREFIX="/api/v1"
  else
    API_PREFIX=""
  fi
fi
BASE_API="$BASE$API_PREFIX"
echo "[smoke] API_PREFIX=$API_PREFIX BASE_API=$BASE_API"


COMPANY_ID="${COMPANY_ID:-1}"
START="${START:-2026-01-01}"
END="${END:-2026-01-31}"
LIMIT="${LIMIT:-5}"

TOTAL=12
step(){ echo; echo "[$1/$TOTAL] $2"; }

fail() { echo "❌ $*"; exit 1; }

# req_json <timeout> <METHOD> <URL> <OUTFILE> [curl_args...]
# - salva body em OUTFILE
# - valida HTTP 2xx
# - valida JSON (jq)
req_json() {
  restore_auth
  local timeout="$1"; local method="$2"; local url="$3"; local out="$4"; shift 4
  local code
  code_file="${TMPDIR:-/tmp}/ia-cnpj_code_$$.out"
  curl_auth -sS --max-time "$timeout" -o "$out" -w '%{http_code}' -X "$method" "$url" "$@" || echo "000" >"${code_file}"
  code=""  # não carregar payload em variável (evita rc=139)

  if [[ ! "$code" =~ ^2[0-9][0-9]$ ]]; then
    echo "❌ HTTP $code $method $url"
    if [ -s "$out" ]; then cat "$out" | jq . >/dev/null 2>&1 && cat "$out" | jq . || cat "$out"; else echo "(sem body)"; fi
    return 1
  fi

  if ! jq -e . "$out" >/dev/null 2>&1; then
    echo "❌ JSON inválido $method $url"
    cat "$out" || true
    return 1
  fi
  return 0
}

# garante COMPANY_ID válido (DB zerado proof)
SMOKE_CNPJ="${SMOKE_CNPJ:-12345678000195}"
SMOKE_RAZAO="${SMOKE_RAZAO:-__SMOKE_COMPANY__ LTDA}"

ensure_company() {
  # sanitize CR invisível
  COMPANY_ID="${COMPANY_ID//$'^M'/}"

  if [[ ! "$COMPANY_ID" =~ ^[0-9]+$ ]]; then
    echo "❌ COMPANY_ID inválido: $COMPANY_ID"
    return 1
  fi

  get_tmp="/tmp/smoke_pre_company_get.json"
  get_code_file="${TMPDIR:-/tmp}/ia-cnpj_get_code_$$.out"
  curl_auth -sS --max-time 5 -o "$get_tmp" -w '%{http_code}' "$BASE/companies/$COMPANY_ID" || echo "000" >"${get_code_file}"
  get_code=""  # não carregar payload em variável (evita rc=139)

  if [[ "$get_code" =~ ^2[0-9][0-9]$ ]]; then
    # existe
    return 0
  fi

  echo "ℹ️ preflight: company_id=$COMPANY_ID não existe (HTTP $get_code); seed/lookup por CNPJ..."

  payload="$(jq -nc --arg cnpj "$SMOKE_CNPJ" --arg rs "$SMOKE_RAZAO" '{cnpj:$cnpj, razao_social:$rs}')"

  seed_tmp="/tmp/smoke_pre_seed_company.json"
  seed_url="$BASE/companies"
  seed_code_file="${TMPDIR:-/tmp}/ia-cnpj_seed_code_$$.out"
  curl_auth -sS --max-time 6 -o "$seed_tmp" -w '%{http_code}' "$seed_url" \
    -H 'Content-Type: application/json' \
    -d "$payload" || echo "000" >"${seed_code_file}"
  seed_code=""  # não carregar payload em variável (evita rc=139)

  if [ "$seed_code" = "404" ]; then
    seed_url="$BASE/api/v1/companies"
    seed_code_file="${TMPDIR:-/tmp}/ia-cnpj_seed_code_$$.out"
    curl_auth -sS --max-time 6 -o "$seed_tmp" -w '%{http_code}' "$seed_url" \
      -H 'Content-Type: application/json' \
      -d "$payload" || echo "000" >"${seed_code_file}"
    seed_code=""  # não carregar payload em variável (evita rc=139)

  fi

  if [ "$seed_code" != "200" ] && [ "$seed_code" != "201" ] && [ "$seed_code" != "409" ]; then
    echo "❌ preflight seed falhou HTTP $seed_code ($seed_url)"
    cat "$seed_tmp" | jq . >/dev/null 2>&1 && cat "$seed_tmp" | jq . || cat "$seed_tmp"
    return 1
  fi

  if [ "$seed_code" = "409" ]; then
    echo "ℹ️ preflight: 409 (CNPJ já cadastrado); buscando id existente..."
    lookup_tmp="/tmp/smoke_pre_lookup_companies.json"
    lookup_url="$seed_url"
    lookup_code_file="${TMPDIR:-/tmp}/ia-cnpj_lookup_code_$$.out"
    curl_auth -sS --max-time 6 -o "$lookup_tmp" -w '%{http_code}' "$lookup_url" || echo "000" >"${lookup_code_file}"
    lookup_code=""  # não carregar payload em variável (evita rc=139)

    if [ "$lookup_code" = "404" ]; then
      lookup_url="$BASE/api/v1/companies"
      lookup_code_file="${TMPDIR:-/tmp}/ia-cnpj_lookup_code_$$.out"
      curl_auth -sS --max-time 6 -o "$lookup_tmp" -w '%{http_code}' "$lookup_url" || echo "000" >"${lookup_code_file}"
      lookup_code=""  # não carregar payload em variável (evita rc=139)

    fi
    existing_id="$(jq -r --arg c "$SMOKE_CNPJ" '..|objects|select(has("cnpj") and .cnpj==$c and has("id"))|.id' "$lookup_tmp" 2>/dev/null | head -n1 || true)"
    if [ -z "$existing_id" ] || [ "$existing_id" = "null" ]; then
      echo "❌ preflight lookup por CNPJ falhou (HTTP $lookup_code $lookup_url)"
      cat "$lookup_tmp" | jq . >/dev/null 2>&1 && cat "$lookup_tmp" | jq . || cat "$lookup_tmp"
      return 1
    fi
    COMPANY_ID="$existing_id"
    echo "ℹ️ preflight: usando COMPANY_ID=$COMPANY_ID (lookup por cnpj)"
    return 0
  fi

  seed_new_id="$(jq -r '.id // .company_id // empty' "$seed_tmp" 2>/dev/null | head -n1 || true)"
  if [ -n "$seed_new_id" ] && [ "$seed_new_id" != "null" ]; then
    COMPANY_ID="$seed_new_id"
    echo "ℹ️ preflight: usando COMPANY_ID=$COMPANY_ID (retornado pelo seed)"
  else
    echo "ℹ️ preflight: seed sem id explícito (seguindo com COMPANY_ID=$COMPANY_ID)"
  fi
  return 0
}

echo "== IA-CNPJ SMOKE =="
echo "BASE=$BASE COMPANY_ID=$COMPANY_ID START=$START END=$END"

step 1 "/health"
out="/tmp/smoke_01_health.json"
req_json 4 GET "$BASE/health" "$out" || fail "step 1 falhou"
echo "OK"

echo "ℹ️ preflight: ensure company (COMPANY_ID=$COMPANY_ID)"
ensure_company || fail "preflight company falhou"
echo "OK"

step 2 "/reports/context"
out="/tmp/smoke_02_reports_context.json"
req_json 6 GET "$BASE_API/reports/context?company_id=$COMPANY_ID&start=$START&end=$END&limit=$LIMIT" "$out" || fail "step 2 falhou"
echo "OK"

step 3 "/reports/top-categories"
out="/tmp/smoke_03_reports_top_categories.json"
req_json 6 GET "$BASE_API/reports/top-categories?company_id=$COMPANY_ID&start=$START&end=$END&metric=saidas&limit=5" "$out" || fail "step 3 falhou"
echo "OK"

step 4 "/transactions/uncategorized"
out="/tmp/smoke_04_tx_uncategorized.json"
req_json 6 GET "$BASE_API/transactions/uncategorized?company_id=$COMPANY_ID&start=$START&end=$END&limit=50" "$out" || fail "step 4 falhou"
echo "OK"

step 5 "/transactions/bulk-categorize"
# pega uncategorized e monta payload items -> seta categoria 1 (se houver)
uncat="/tmp/smoke_05_uncat200.json"
req_json 6 GET "$BASE_API/transactions/uncategorized?company_id=$COMPANY_ID&start=$START&end=$END&limit=200" "$uncat" || fail "step 5 (GET uncat) falhou"
n_uncat="$(jq 'length' "$uncat" 2>/dev/null || echo 0)"
if [ "$n_uncat" = "0" ]; then
  echo "OK (skip): sem uncategorized"
else
  PAYLOAD="$(jq -c --argjson cid "$COMPANY_ID" '{company_id: $cid, items: map({id: .id, category_id: 1})}' "$uncat")"
  out="/tmp/smoke_05_bulk_categorize.json"
  req_json 10 POST "$BASE_API/transactions/bulk-categorize" "$out" \
    -H 'Content-Type: application/json' -d "$PAYLOAD" || fail "step 5 (POST bulk) falhou"
  echo "OK"
fi

step 6 "/transactions/apply-suggestions (dry-run)"
out="/tmp/smoke_06_apply_suggestions_dry.json"
req_json 8 POST "$BASE_API/transactions/apply-suggestions?company_id=$COMPANY_ID&start=$START&end=$END&limit=200&dry_run=true" "$out" || fail "step 6 falhou"
echo "OK"

step 7 "/transactions/apply-suggestions (apply)"
out="/tmp/smoke_07_apply_suggestions_apply.json"
req_json 8 POST "$BASE_API/transactions/apply-suggestions?company_id=$COMPANY_ID&start=$START&end=$END&limit=200" "$out" || fail "step 7 falhou"
echo "OK"

step 8 "/ai/suggest-categories"
out="/tmp/smoke_08_ai_suggest.json"
req_json 8 POST "$BASE_API/ai/suggest-categories" "$out" \
  -H 'Content-Type: application/json' \
  -d "{\"company_id\":$COMPANY_ID,\"start\":\"$START\",\"end\":\"$END\",\"limit\":50,\"include_no_match\":true}" || fail "step 8 falhou"
echo "OK"

step 9 "/ai/apply-suggestions (dry-run)"
out="/tmp/smoke_09_ai_apply_dry.json"
req_json 10 POST "$BASE_API/ai/apply-suggestions" "$out" \
  -H 'Content-Type: application/json' \
  -d "{\"company_id\":$COMPANY_ID,\"start\":\"$START\",\"end\":\"$END\",\"limit\":200,\"dry_run\":true,\"include_no_match\":true}" || fail "step 9 falhou"
echo "OK"

step 10 "/ai/apply-suggestions (apply)"
out="/tmp/smoke_10_ai_apply_apply.json"
req_json 10 POST "$BASE_API/ai/apply-suggestions" "$out" \
  -H 'Content-Type: application/json' \
  -d "{\"company_id\":$COMPANY_ID,\"start\":\"$START\",\"end\":\"$END\",\"limit\":200,\"dry_run\":false}" || fail "step 10 falhou"
echo "OK"


step 11 "/ai/consult"



# contrato mínimo do /ai/consult (não quebra cliente)
echo
echo "[contract] /ai/consult shape + caps"

tmp="/tmp/ai_consult_contract.json"

call_consult () {
  local url="$1"
  curl_auth -sS --max-time 6 -o "$tmp" -w '%{http_code}' "$url" \
    -H 'Content-Type: application/json' \
    -d "{\"company_id\":$COMPANY_ID,\"start\":\"$START\",\"end\":\"$END\",\"limit\":20,\"question\":\"onde estou gastando mais?\"}"
}

consult_url="$BASE/ai/consult"
code="$(call_consult "$consult_url")"

# fallback pra /api/v1 se for Not Found "puro" (rota errada)
if [ "$code" = "404" ] && jq -e '.detail=="Not Found"' "$tmp" >/dev/null 2>&1; then
  consult_url="$BASE/api/v1/ai/consult"
  code="$(call_consult "$consult_url")"
fi

# se faltar company, tenta seed + retry 1x (CI às vezes vem DB zerado)
if [ "$code" != "200" ] && jq -e '.detail.error_code=="COMPANY_NOT_FOUND"' "$tmp" >/dev/null 2>&1; then
  echo "ℹ️ company_id=$COMPANY_ID não existe; tentando seed..."

  seed_tmp="/tmp/ai_consult_seed_company.json"
  seed_url="$BASE/companies"
  seed_code_file="${TMPDIR:-/tmp}/ia-cnpj_seed_code_$$.out"
  curl_auth -sS --max-time 6 -o "$seed_tmp" -w '%{http_code}' "$seed_url" \
    -H 'Content-Type: application/json' \
    -d '{"cnpj":"12345678000195","razao_social":"__SMOKE_COMPANY__ LTDA"}' >"${seed_code_file}"
  seed_code=""  # não carregar payload em variável (evita rc=139)

  # fallback pra /api/v1/companies se necessário
  if [ "$seed_code" = "404" ]; then
    seed_url="$BASE/api/v1/companies"
    seed_code_file="${TMPDIR:-/tmp}/ia-cnpj_seed_code_$$.out"
    curl_auth -sS --max-time 6 -o "$seed_tmp" -w '%{http_code}' "$seed_url" \
      -H 'Content-Type: application/json' \
      -d '{"cnpj":"12345678000195","razao_social":"__SMOKE_COMPANY__ LTDA"}' >"${seed_code_file}"
    seed_code=""  # não carregar payload em variável (evita rc=139)

  fi
  if [ "$seed_code" != "200" ] && [ "$seed_code" != "201" ] && [ "$seed_code" != "409" ]; then
    echo "❌ seed company falhou HTTP $seed_code ($seed_url)"
    cat "$seed_tmp" | jq . || cat "$seed_tmp"
    exit 1
  fi
  if [ "$seed_code" = "409" ]; then
    echo "ℹ️ seed retornou 409 (CNPJ já cadastrado); buscando id existente..."
    lookup_tmp="/tmp/ai_consult_lookup_company.json"
    lookup_url="$seed_url"
    lookup_code_file="${TMPDIR:-/tmp}/ia-cnpj_lookup_code_$$.out"
    curl_auth -sS --max-time 6 -o "$lookup_tmp" -w '%{http_code}' "$lookup_url" >"${lookup_code_file}"
    lookup_code=""  # não carregar payload em variável (evita rc=139)

    if [ "$lookup_code" = "404" ]; then
      lookup_url="$BASE/api/v1/companies"
      lookup_code_file="${TMPDIR:-/tmp}/ia-cnpj_lookup_code_$$.out"
      curl_auth -sS --max-time 6 -o "$lookup_tmp" -w '%{http_code}' "$lookup_url" >"${lookup_code_file}"
      lookup_code=""  # não carregar payload em variável (evita rc=139)

    fi
    existing_id="$(jq -r --arg c "12345678000195" '..|objects|select(has("cnpj") and .cnpj==$c and has("id"))|.id' "$lookup_tmp" 2>/dev/null | head -n1 || true)"
    if [ -z "$existing_id" ] || [ "$existing_id" = "null" ]; then
      echo "❌ lookup de company por CNPJ falhou (HTTP $lookup_code $lookup_url)"
      cat "$lookup_tmp" | jq . || cat "$lookup_tmp"
      exit 1
    fi
    COMPANY_ID="$existing_id"
    consult_url="$(echo "$consult_url" | sed -E "s/(company_id=)[0-9]+/\1$COMPANY_ID/")"
    echo "ℹ️ usando COMPANY_ID=$COMPANY_ID (lookup por cnpj)"
  fi

  echo "✅ seed company OK ($seed_url). Retentando consult..."
  seed_new_id="$(jq -r '.id // .company_id // empty' "$seed_tmp" 2>/dev/null || true)"
  if [ -n "$seed_new_id" ] && [ "$seed_new_id" != "null" ]; then
    COMPANY_ID="$seed_new_id"
    echo "ℹ️ usando COMPANY_ID=$COMPANY_ID (retornado pelo seed)"
  fi
  code="$(call_consult "$consult_url")"
fi

if [ "$code" != "200" ]; then
  echo "❌ /ai/consult HTTP $code ($consult_url)"
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


curl_auth -sS --max-time 6 -H 'Content-Type: application/json' \
  -d "{\"company_id\":$COMPANY_ID,\"start\":\"$START\",\"end\":\"$END\",\"limit\":10,\"question\":\"smoke\"}" \
  "$BASE_API/ai/consult" | jq -e . >/dev/null
echo "OK"

echo

step 12 "reports ai-consult pdf (/reports/ai-consult/pdf)"

# valida: HTTP 200 + content-type=application/pdf + magic %PDF
SMOKE_AUTH_HEADER_FILE="${__hdr:-/tmp/ia_cnpj_auth_header}" python - <<'PY_PDF'
import json, os, urllib.request

base = os.environ.get("BASE", "http://127.0.0.1:8100").rstrip("/")
prefix = os.environ.get("API_PREFIX", "")
url = f"{base}{prefix}/reports/ai-consult/pdf"

payload = {
    "company_id": int(os.environ.get("COMPANY_ID", "1")),
    "period": {"start": os.environ.get("START", "2026-01-01"), "end": os.environ.get("END", "2026-01-31")},
    "dry_run": False,
    "include_no_match": True,
}

# auth-aware headers (respeita AUTH_ENABLED)

import os, json

from urllib.request import Request, urlopen

from urllib.error import HTTPError


headers = {"Content-Type": "application/json", "Accept": "application/pdf"}

auth_enabled = os.getenv("AUTH_ENABLED", "").lower() in ("1","true","yes","on")

if auth_enabled:

    user = os.getenv("AUTH_USERNAME", "dev")

    pw = os.getenv("AUTH_PASSWORD") or os.getenv("AUTH_PLAIN_PASSWORD") or "dev"

    payload_login = json.dumps({"username": user, "password": pw}).encode("utf-8")


    token = None

    for login_url in (f"{base}{prefix}/auth/login", f"{base}/auth/login"):

        try:

            req = Request(login_url, data=payload_login, headers={"Content-Type": "application/json"})

            with urlopen(req, timeout=20) as r:

                body = r.read().decode("utf-8")

            token = json.loads(body).get("access_token")

            if token:

                break

        except HTTPError:

            pass


    if not token:

        raise SystemExit("FAIL auth: AUTH_ENABLED=true mas não consegui obter access_token")

    headers["Authorization"] = f"Bearer {token}"
hdr_file = os.environ.get("SMOKE_AUTH_HEADER_FILE", "")
if hdr_file:
    try:
        txt = open(hdr_file, "r", encoding="utf-8").read().strip()
        if txt.lower().startswith("authorization:"):
            headers["Authorization"] = txt.split(":", 1)[1].strip()
    except FileNotFoundError:
        pass

data = json.dumps(payload).encode("utf-8")
req = urllib.request.Request(url, data=data, headers=headers, method="POST")

with urllib.request.urlopen(req, timeout=30) as r:
    ct = (r.headers.get("Content-Type") or "").lower()
    head = r.read(4)
    if r.status != 200:
        raise SystemExit(f"FAIL pdf http={r.status}")
    if "application/pdf" not in ct:
        raise SystemExit(f"FAIL pdf content-type={ct}")
    if head != b"%PDF":
        raise SystemExit("FAIL pdf magic (não começa com %PDF)")
print("OK pdf /reports/ai-consult/pdf")
PY_PDF
echo "✅ SMOKE PASS"
