#!/usr/bin/env bash
set -euo pipefail


CURL_AUTH=()
CURL_AUTH_KEEP=()

restore_auth() {
  if [[ ${#CURL_AUTH_KEEP[@]} -eq 0 ]] && [[ ${#CURL_AUTH[@]} -gt 0 ]]; then
    CURL_AUTH_KEEP=()
  fi
  if [[ "${_auth_enabled:-}" == "true" ]] && [[ ${#CURL_AUTH[@]} -eq 0 ]] && [[ ${#CURL_AUTH_KEEP[@]} -gt 0 ]]; then
    CURL_AUTH=("${CURL_AUTH_KEEP[@]}")
  fi
}

curl_auth() {
  # AUTO_LOGIN_ON_DEMAND: se auth está ligado e não temos token, faz login antes do request
  if [[ ${#CURL_AUTH[@]} -eq 0 ]]; then
    local _enabled="${IA_CNPJ_AUTH_ENABLED:-${AUTH_ENABLED:-}}"
    if [[ "${_enabled}" == "true" || "${_enabled}" == "1" ]]; then
      local _user="${SMOKE_AUTH_USER:-}" _pass="${SMOKE_AUTH_PASS:-}"
      if [[ -z "${_user}" || -z "${_pass}" ]]; then
        echo "❌ SMOKE_AUTH_USER/SMOKE_AUTH_PASS obrigatórios quando auth está ligado" >&2
        exit 1
      fi

      local _login_url="${BASE%/}/auth/login"
      local _tmp _code _tok _i
      local _was_x=0
      [[ "${SHELLOPTS:-}" == *xtrace* || "$-" == *x* ]] && _was_x=1
      (( _was_x )) && set +x

      for _i in {1..25}; do
        _tmp="$(mktemp)"
        _code="$(command curl -sS --max-time 6 -o "${_tmp}" -w '%{http_code}' \
          -X POST "${_login_url}" \
          -H 'Content-Type: application/json' \
          -d "{\"username\":\"${_user}\",\"password\":\"${_pass}\"}" || true
        )"

        _tok=""
        if command -v jq >/dev/null 2>&1; then
          _tok="$(jq -er '.access_token' "${_tmp}" 2>/dev/null || true)"
        fi
        if [[ -z "${_tok}" ]]; then
          _tok="$(sed -n 's/.*"access_token"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "${_tmp}" | head -n1)"
        fi
        rm -f "${_tmp}"

        if [[ "${_code}" == 2* && -n "${_tok}" ]]; then
          CURL_AUTH=(-H "Authorization: Bearer ${_tok}")
          CURL_AUTH_KEEP=("${CURL_AUTH[@]}")
          break
        fi
        sleep 0.2
      done

      (( _was_x )) && set -x

      if [[ ${#CURL_AUTH[@]} -eq 0 ]]; then
        echo "❌ falhou pegar access_token do /auth/login (auto-login do curl_auth)" >&2
        exit 1
      fi
    fi
  fi

  # roda curl_auth com header global sem vazar em xtrace
  local _was_x=0
  [[ "${SHELLOPTS:-}" == *xtrace* || "$-" == *x* ]] && _was_x=1
  (( _was_x )) && set +x
  command curl "$@"
  local rc=$?
  # xtrace será restaurado após setar CURL_AUTH
  return $rc
}

# AUTH_PREFLIGHT (auto)
# se a API disser auth_enabled=true, faz login e seta header (sem vazar no xtrace)
: "${BASE_API:=http://127.0.0.1:8100}"
_health_json="$(curl_auth -sS "${BASE_API%/}/health" 2>/dev/null || true)"
if command -v jq >/dev/null 2>&1; then
  _auth_enabled="$(printf '%s' "$_health_json" | jq -r '.auth_enabled // false' 2>/dev/null || echo false)"
else
  _auth_enabled=false
fi

if [[ "${_auth_enabled}" == "true" ]]; then
  _u="${SMOKE_AUTH_USER:-${IA_CNPJ_AUTH_USERNAME:-${AUTH_USERNAME:-admin}}}"
  _p="${SMOKE_AUTH_PASS:-${IA_CNPJ_AUTH_PASSWORD:-${AUTH_PASSWORD:-}}}"
  if [[ -z "${_p}" ]]; then
    echo "❌ smoke auth: senha ausente (set SMOKE_AUTH_PASS ou IA_CNPJ_AUTH_PASSWORD/AUTH_PASSWORD)" >&2
    exit 1
  fi
  _tok_json="$(curl_auth -sS -X POST "${BASE_API%/}/auth/login" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    --data-urlencode "username=${_u}" \
    --data-urlencode "password=${_p}" )"
  _tok="$(printf '%s' "$_tok_json" | jq -r '.access_token // empty' 2>/dev/null || echo '')"
  if [[ -z "${_tok}" ]]; then
    echo "❌ falhou pegar access_token (auth enabled)" >&2
    exit 1
  fi
  CURL_AUTH=(-H "Authorization: Bearer ${_tok}")
fi


# --- curl_auth helper: retorna JSON completo, sem truncar, e valida com jq ---
_curl_json() {
  local method="$1"; shift
  local url="$1"; shift
  local body="${1-}"

  local tmp_body tmp_code
  tmp_body="$(mktemp)"
  tmp_code="$(mktemp)"

  if [[ -n "$body" ]]; then
    curl_auth -sS --max-time 30 -X "$method" "$url" \
      -H "Content-Type: application/json" \
      --data "$body" \
      -o "$tmp_body" -w '%{http_code}' > "$tmp_code"
  else
    curl_auth -sS --max-time 30 -X "$method" "$url" \
      -o "$tmp_body" -w '%{http_code}' > "$tmp_code"
  fi

  local code
  code="$(cat "$tmp_code" 2>/dev/null || true)"

  if jq -e . < "$tmp_body" >/dev/null 2>&1; then
    cat "$tmp_body"
    rm -f "$tmp_body" "$tmp_code"
    return 0
  fi

  echo "❌ resposta não-JSON ou truncada (HTTP=$code) url=$url" >&2
  echo "--- body (first 800 bytes) ---" >&2
  head -c 800 "$tmp_body" >&2
  echo >&2
  rm -f "$tmp_body" "$tmp_code"
  return 1
}


: "${LIMIT:=200}"
: "${INCLUDE_NO_MATCH:=true}"

API="${API_CNPJ:-http://127.0.0.1:8100}"
API="$(printf '%s' "$API" | tr -d '\r')"
BASE="$API"
# AUTH_BOOTSTRAP_EARLY (auto)
type die >/dev/null 2>&1 || die(){ echo "❌ $*"; exit 1; }

# detecta auth_enabled via /health e faz login ANTES de qualquer /companies
_auth_enabled=""
_health_json="$(curl_auth -sS --max-time 3 "$BASE/health" || true)"
if command -v jq >/dev/null 2>&1; then
  _auth_enabled="$(printf %s "$_health_json" | jq -er '.auth_enabled // false' 2>/dev/null || true)"
fi
if [[ -z "${_auth_enabled:-}" ]]; then
  _auth_enabled="$(printf %s "$_health_json" | sed -n 's/.*"auth_enabled"[[:space:]]*:[[:space:]]*\([^,}]*\).*/\1/p')"
fi
[[ "${_auth_enabled:-}" == "true" ]] && _auth_enabled=true || _auth_enabled=false

if [[ "${_auth_enabled}" == "true" ]] && [[ ${#CURL_AUTH[@]} -eq 0 ]]; then
  _user="${SMOKE_AUTH_USER:-}"; _pass="${SMOKE_AUTH_PASS:-}"
  [[ -z "$_user" || -z "$_pass" ]] && die "SMOKE_AUTH_USER/SMOKE_AUTH_PASS obrigatórios quando auth_enabled=true"
  _login_url="$BASE/auth/login"
  _tmp="$(mktemp)"
  _was_x=0; [[ "${SHELLOPTS:-}" == *xtrace* || "$-" == *x* ]] && _was_x=1
  (( _was_x )) && set +x
  _code="$(curl_auth -sS --max-time 6 -o "$_tmp" -w '%{http_code}' -X POST "$_login_url" \
    -H 'Content-Type: application/json' \
    -d "{\"username\":\"$_user\",\"password\":\"$_pass\"}" || true)"
  _tok=""
  if command -v jq >/dev/null 2>&1; then
    _tok="$(jq -er '.access_token' "$_tmp" 2>/dev/null || true)"
  fi
  if [[ -z "$_tok" ]]; then
    _tok="$(sed -n 's/.*"access_token"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$_tmp" | head -n1)"
  fi
  rm -f "$_tmp"
  [[ "${_code}" != 2* || -z "$_tok" ]] && die "falhou pegar access_token do /auth/login"
  CURL_AUTH=(-H "Authorization: Bearer $_tok")
  CURL_AUTH_KEEP=("${CURL_AUTH[@]}")
  restore_auth
  (( _was_x )) && set -x
fi


# autodetect prefix (/api/v1) via OpenAPI (compat)
API_PREFIX="${API_PREFIX:-}"
if [ -z "$API_PREFIX" ]; then
  oa="$(curl_auth -sS --max-time 6 "$BASE/openapi.json" || true)"
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

# pattern esperado (por regra atual): "internet|wifi|provedor" -> category_id=6
DESC="${DESC:-internet fibra}"
AMOUNT="${AMOUNT:-4500}"
KIND="${KIND:-out}"
OCCURRED_AT="${OCCURRED_AT:-2026-01-15T12:00:00}"

# se CLEANUP=1, tenta apagar a tx no final (se existir endpoint; se não, só avisa)
CLEANUP="${CLEANUP:-0}"

die(){ echo "❌ $*" >&2; exit 1; }

need() { command -v "$1" >/dev/null 2>&1 || die "precisa de '$1' instalado"; }
need curl_auth
need jq

is_json() { jq -e . >/dev/null 2>&1; }
curl_json() {
  # uso: curl_json METHOD URL [JSON_BODY]
  # imprime SOMENTE o body em stdout quando for JSON válido
  local method="$1"; shift
  local url="$1"; shift
  local body="${1-}"

  local tmp_body tmp_code
  tmp_body="$(mktemp)"
  tmp_code="$(mktemp)"

  if [[ -n "$body" ]]; then
    curl_auth -sS --max-time 30 -X "$method" "$url" \
      -H "Content-Type: application/json" \
      --data "$body" \
      -o "$tmp_body" -w '%{http_code}' > "$tmp_code"
  else
    curl_auth -sS --max-time 30 -X "$method" "$url" \
      -o "$tmp_body" -w '%{http_code}' > "$tmp_code"
  fi

  local code
  code="$(cat "$tmp_code" 2>/dev/null || true)"

  # valida JSON
  if jq -e . < "$tmp_body" >/dev/null 2>&1; then
    cat "$tmp_body"
    rm -f "$tmp_body" "$tmp_code"
    return 0
  fi

  echo "❌ resposta não-JSON ou truncada (HTTP=$code) url=$url" >&2
  echo "--- body (first 600 bytes) ---" >&2
  head -c 600 "$tmp_body" >&2
  echo >&2
  rm -f "$tmp_body" "$tmp_code"
  return 2
}



echo "== IA-CNPJ SMOKE (AI suggest/apply) =="

SMOKE_TAG="__SMOKE_AI__$(date +%Y%m%d_%H%M%S)"
echo "API=$API COMPANY_ID=$COMPANY_ID PERIOD=$START..$END"

echo

echo
echo "[0/5] garante company_id=$COMPANY_ID (seed idempotente)"
  # sanitize: remove CR/LF/TAB/espacos (corrige 8100^M e quoting zoado)
  API="$(printf %s "$API" | tr -d '\r\n\t ')"
  COMPANY_ID="$(printf %s "$COMPANY_ID" | tr -d '\r\n\t ')"

  SMOKE_CNPJ="${SMOKE_CNPJ:-00000000000191}"
  SMOKE_RAZAO="${SMOKE_RAZAO:-Empresa Smoke}"

  get_tmp="/tmp/smoke_ai_get_company.json"
  get_url="$API/companies/$COMPANY_ID"
  get_code="$(curl_auth -sS --max-time 5 -o "$get_tmp" -w '%{http_code}' "$get_url" || echo "000")"

  if [[ "$get_code" =~ ^2[0-9][0-9]$ ]] && jq -e '.id' "$get_tmp" >/dev/null 2>&1; then
    echo "OK: company_id=$COMPANY_ID existe"
  else
    echo "ℹ️ company_id=$COMPANY_ID não existe (HTTP $get_code); criando/recuperando empresa smoke..."

    COMP_PAYLOAD="$(jq -nc --arg cnpj "$SMOKE_CNPJ" --arg rs "$SMOKE_RAZAO" '{cnpj:$cnpj, razao_social:$rs}')"

    seed_tmp="/tmp/smoke_ai_seed_company.json"
# auth: pega token (se auth_enabled=true)
if [[ "${_auth_enabled:-false}" == "true" ]]; then
  _user="${SMOKE_AUTH_USER:-}"
  _pass="${SMOKE_AUTH_PASS:-}"
  [[ -z "$_user" || -z "$_pass" ]] && die "SMOKE_AUTH_USER/SMOKE_AUTH_PASS obrigatórios quando auth_enabled=true"
  _login_url="$BASE/auth/login"
  _login_tmp="$(mktemp)"
  _was_x=0; [[ "${SHELLOPTS:-}" == *xtrace* || "$-" == *x* ]] && _was_x=1
  (( _was_x )) && set +x
  _code="$(curl_auth -sS --max-time 6 -o "$_login_tmp" -w '%{http_code}' -X POST "$_login_url" \
    -H 'Content-Type: application/json' \
    -d "{\"username\":\"$_user\",\"password\":\"$_pass\"}" || true)"
  (( _was_x )) && set -x
  [[ "$_code" != 2* ]] && { cat "$_login_tmp" >/dev/stderr || true; die "falhou pegar access_token do /auth/login"; }
  _tok="$(jq -er '.access_token' "$_login_tmp" 2>/dev/null || true)"
  rm -f "$_login_tmp"
  [[ -z "$_tok" ]] && die "falhou extrair access_token do /auth/login"
  CURL_AUTH=(-H "Authorization: Bearer $_tok")
  restore_auth
  (( _was_x )) && set -x
fi
    seed_url="$API/companies"
    seed_code="$(curl_auth -sS --max-time 6 -o "$seed_tmp" -w '%{http_code}' "$seed_url" \
      -H 'Content-Type: application/json' \
      -d "$COMP_PAYLOAD" || echo "000")"

    # fallback /api/v1/companies
    if [ "$seed_code" = "404" ]; then
      seed_url="$API/api/v1/companies"
      seed_code="$(curl_auth -sS --max-time 6 -o "$seed_tmp" -w '%{http_code}' "$seed_url" \
        -H 'Content-Type: application/json' \
        -d "$COMP_PAYLOAD" || echo "000")"
    fi

    if [ "$seed_code" = "409" ]; then
      echo "ℹ️ CNPJ já cadastrado; buscando id existente..."
      lookup_tmp="/tmp/smoke_ai_lookup_company.json"
      lookup_url="$seed_url"
      lookup_code="$(curl_auth -sS --max-time 6 -o "$lookup_tmp" -w '%{http_code}' "$lookup_url" || echo "000")"
      if [ "$lookup_code" = "404" ]; then
        lookup_url="$API/api/v1/companies"
        lookup_code="$(curl_auth -sS --max-time 6 -o "$lookup_tmp" -w '%{http_code}' "$lookup_url" || echo "000")"
      fi
      new_id="$(jq -r --arg c "$SMOKE_CNPJ" '..|objects|select(has("cnpj") and .cnpj==$c and has("id"))|.id' "$lookup_tmp" 2>/dev/null | head -n1 || true)"
    elif [ "$seed_code" = "200" ] || [ "$seed_code" = "201" ]; then
      new_id="$(jq -r '.id // .company_id // .data.id // .data.company_id // empty' "$seed_tmp" 2>/dev/null | head -n1 || true)"
    else
      echo "❌ seed company smoke falhou HTTP $seed_code ($seed_url)"
      cat "$seed_tmp" | jq . >/dev/null 2>&1 && cat "$seed_tmp" | jq . || cat "$seed_tmp"
      die "seed company smoke falhou"
    fi

    [[ "$new_id" =~ ^[0-9]+$ ]] || die "id inválido ao criar/achar empresa: $new_id"
    COMPANY_ID="$new_id"
    echo "OK: usando company_id=$COMPANY_ID"
  fi

echo "[1/5] health"
curl_auth -sS --max-time 5 "$API/health" | jq . >/dev/null

# auth_enabled (via /health)
_auth_enabled=""
_health_json="$(curl_auth -sS --max-time 3 "$BASE/health" || true)"
if command -v jq >/dev/null 2>&1; then
  _auth_enabled="$(printf %s "$_health_json" | jq -er '.auth_enabled // false' 2>/dev/null || true)"
fi
if [[ -z "${_auth_enabled:-}" ]]; then
  _auth_enabled="$(printf %s "$_health_json" | sed -n 's/.*"auth_enabled"[[:space:]]*:[[:space:]]*\\([^,}]*\\).*/\\1/p')"
fi
[[ "${_auth_enabled:-}" == "true" ]] && _auth_enabled="true" || _auth_enabled="false"echo "OK"

echo
echo "[2/5] cria transação sem categoria (category_id=null)"
PAYLOAD="$(jq -n --argjson company_id "$COMPANY_ID" \
                --arg occurred_at "$OCCURRED_AT" \
                --arg kind "$KIND" \
                --argjson amount_cents "$AMOUNT" \
                --arg description "$DESC" \
  '{company_id:$company_id, occurred_at:$occurred_at, kind:$kind, amount_cents:$amount_cents, description:$description}')"

TX_CREATE="$(curl_json POST "$API/transactions" "$PAYLOAD")" || exit $?

# se o backend respondeu erro (JSON sem .id), mostra e morre bonito
if ! echo "$TX_CREATE" | jq -e 'has("id")' >/dev/null 2>&1; then
  echo "❌ /transactions falhou. Resposta:" >&2
  echo "$TX_CREATE" | jq . >&2 || echo "$TX_CREATE" >&2
  exit 2
fi

TX_ID="$(jq -r '.id' <<<"$TX_CREATE")"
TX_CAT="$(jq -r '.category_id' <<<"$TX_CREATE")"

[[ "$TX_ID" =~ ^[0-9]+$ ]] || die "tx_id inválido: $TX_ID"
[[ "$TX_CAT" == "null" ]] || die "esperava category_id null ao criar, veio: $TX_CAT"

echo "OK: tx_id=$TX_ID category_id=null desc="internet fibra ${SMOKE_TAG}""

echo
echo
echo "[3/5] suggest-categories (deve sugerir pro tx_id=$TX_ID)"
# captura resposta do suggest em variável global para os próximos passos
PAYLOAD_SUGG="$(jq -nc --argjson cid "$COMPANY_ID" --arg s "$START" --arg e "$END" \
  '{company_id:$cid, start_date:$s, end_date:$e, include_no_match:true}')"

SUGG="$(curl_json POST "$API/ai/suggest-categories" "$PAYLOAD_SUGG")" || exit $?
  # fonte única pro [5/5]
  SUG_JSON="$SUGG"

# valida que veio sugestão pro TX_ID
echo "$SUGG" | jq -e --argjson tx "$TX_ID" '.items | any(.id == $tx)' >/dev/null \
  || { echo "❌ não apareceu sugestão pro tx_id=$TX_ID"; echo "$SUGG" | jq '{period, count:(.items|length), sample:(.items[0])}'; exit 4; }

echo "OK"
APPLY_BODY_DRY="$(jq -nc --argjson cid "$COMPANY_ID" --arg s "$START" --arg e "$END" --argjson lim "$LIMIT" --argjson inm "$INCLUDE_NO_MATCH" '{
  company_id:$cid, start_date:$s, end_date:$e, limit:$lim, dry_run:true, include_no_match:$inm
}')"
APPLY_BODY_REAL="$(jq -nc --argjson cid "$COMPANY_ID" --arg s "$START" --arg e "$END" --argjson lim "$LIMIT" --argjson inm "$INCLUDE_NO_MATCH" '{
  company_id:$cid, start_date:$s, end_date:$e, limit:$lim, dry_run:false, include_no_match:$inm
}')"

echo "[4/5] apply-suggestions dry_run=true (deve contar 1)"
# dry_run pode sugerir >1 se tiver lixo no banco; então validamos por TX_ID.
resp="$(curl_json POST "$API/ai/apply-suggestions" "$APPLY_BODY_DRY")" || exit 1
suggested="$(echo "$resp" | jq -r '.suggested // 0')"
has_tx="$(echo "$resp" | jq -r --argjson id "$TX_ID" '.items | any(.id == $id)')"

if [[ "$suggested" -lt 1 ]]; then
  echo "❌ dry_run esperado suggested>=1, veio: $suggested"
  exit 1
fi
if [[ "$has_tx" != "true" ]]; then
  echo "❌ dry_run não incluiu o TX_ID=$TX_ID nas sugestões (banco pode estar estranho)"
  echo "$resp" | jq '{period, suggested, updated, sample:(.items[0] // null)}'
  exit 1
fi

echo "OK (dry_run): suggested=$suggested inclui TX_ID=$TX_ID"
echo "[5/5] apply-suggestions dry_run=false (aplica) + valida TX_ID via /transactions/{tx_id}/category"

# pega categoria sugerida específica pro TX_ID
[[ -n "${SUG_JSON:-}" ]] || SUG_JSON="${SUGGEST_JSON:-${SUG:-${SUG_BODY_JSON:-}}}"
SUG_CAT="$(echo "$SUG_JSON" | jq -r --argjson tx "$TX_ID" '.items[] | select(.id==$tx) | .suggested_category_id' | head -n 1)"
if [[ -z "${SUG_CAT:-}" || "$SUG_CAT" == "null" ]]; then
  echo "❌ não achei suggested_category_id para TX_ID=$TX_ID no SUG_JSON" >&2
  echo "$SUG_JSON" | head -c 800 >&2
  echo >&2
  exit 1
fi

# aplica usando endpoint batch (pode atualizar outros, mas a gente valida o TX_ID)
APPLY_BODY_REAL="$(jq -nc \
  --argjson company_id "$COMPANY_ID" \
  --arg start "$START" --arg end "$END" \
  --argjson limit "$LIMIT" \
  '{company_id:$company_id,start_date:$start,end_date:$end,limit:$limit,dry_run:false}')"

APPLY_JSON="$(_curl_json POST "$API/ai/apply-suggestions" "$APPLY_BODY_REAL")"

updated="$(echo "$APPLY_JSON" | jq -r '.updated // 0')"
echo "OK (apply batch): updated=$updated (validando TX_ID=$TX_ID)"

# valida TX_ID direto na lista /transactions (não depende do batch ter vindo limpo)
TX_ROW="$(_curl_json GET "$API/transactions?company_id=$COMPANY_ID&limit=500")"
TX_CAT="$(echo "$TX_ROW" | jq -r --argjson tx "$TX_ID" '.[] | select(.id==$tx) | .category_id' | head -n 1)"

if [[ "$TX_CAT" != "$SUG_CAT" ]]; then
  echo "❌ TX_ID=$TX_ID não ficou categorizado: esperado category_id=$SUG_CAT, veio $TX_CAT" >&2
  exit 1
fi


echo
echo "[6/6] idempotência: re-apply apply-suggestions dry_run=true deve ser 0"

# bash strict (-u): garante variáveis definidas
: "${PERIOD_FROM:=}"
: "${PERIOD_TO:=}"

# garante período (suporta PERIOD=YYYY-MM-DD..YYYY-MM-DD)
if [[ -z "${PERIOD_FROM:-}" || -z "${PERIOD_TO:-}" ]]; then
  if [[ -n "${PERIOD:-}" && "${PERIOD}" == *".."* ]]; then
    PERIOD_FROM="${PERIOD%%..*}"
    PERIOD_TO="${PERIOD##*..}"
  fi
fi

# tenta reaproveitar corpo/url já usados no apply principal
_IDEM_BODY="${apply_body:-${APPLY_BODY:-${SUG_BODY:-${SUGGEST_BODY:-}}}}"
if [[ -z "${_IDEM_BODY}" ]]; then
  _IDEM_BODY="$(jq -n --argjson company_id "${COMPANY_ID}" \
    --arg period_from "${PERIOD_FROM}" --arg period_to "${PERIOD_TO}" \
    '{company_id:$company_id, period_from:$period_from, period_to:$period_to}')"
fi

_BASE_APPLY_URL="${apply_url:-${APPLY_URL:-${API%/}/ai/suggest/apply}}"
_IDEM_URL="${_BASE_APPLY_URL}?dry_run=true"

_IDEM_RESP="$(curl_auth -sS -X POST "${_IDEM_URL}" -H 'Content-Type: application/json' -d "${_IDEM_BODY}" || true)"
_IDEM_SUG="$(echo "${_IDEM_RESP}" | jq -r 'try (.suggested // .count // (.items|length) // (.suggestions|length) // 0) catch "__BADJSON__"')"

if [[ "${_IDEM_SUG}" == "__BADJSON__" ]]; then
  echo "❌ idempotência: resposta não-JSON no re-apply"
  echo "${_IDEM_RESP}" | head -c 600
  exit 1
fi

if [[ "${_IDEM_SUG}" != "0" ]]; then
  echo "❌ idempotência falhou: esperado suggested=0 no re-apply; veio suggested=${_IDEM_SUG}"
  echo "${_IDEM_RESP}" | head -c 600
  exit 1
fi

echo "OK (idempotência): suggested=0"
echo "✅ SMOKE PASS (TX_ID=$TX_ID category_id=$TX_CAT)"
