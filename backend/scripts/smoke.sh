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
# ⚠️ workaround: em alguns ambientes o bash está segfaultando durante o autodetect.
# Default: NÃO autodetecta. Se precisar, use SMOKE_DETECT_PREFIX=1 ou defina API_PREFIX manualmente.
API_PREFIX="${API_PREFIX:-}"
if [ -z "$API_PREFIX" ]; then
  if [ "${SMOKE_DETECT_PREFIX:-0}" = "1" ]; then
    oa_file="${TMPDIR:-/tmp}/ia-cnpj_openapi_$$.json"
    curl_auth -sS --connect-timeout 1 --max-time 15 "$_BASE/openapi.json" >"$oa_file"
    if jq -e '.paths["/api/v1/ai/consult"]' "$oa_file" >/dev/null 2>&1; then
      API_PREFIX="/api/v1"
    else
      API_PREFIX=""
    fi
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
  SMOKE_AUTH_HEADER_FILE="${__hdr:-/tmp/ia_cnpj_auth_header}" \
  REQ_TIMEOUT="$timeout" REQ_METHOD="$method" REQ_URL="$url" REQ_OUT="$out" \
  python - "$@" <<'PY_REQ'
import json, os, sys, urllib.request
from urllib.error import HTTPError

timeout = float(os.environ.get('REQ_TIMEOUT','10'))
method = os.environ.get('REQ_METHOD','GET')
url = os.environ.get('REQ_URL','').strip()
out = os.environ.get('REQ_OUT','/tmp/req.out')
hdr_file = os.environ.get('SMOKE_AUTH_HEADER_FILE','')

headers = {}
data = None

# parse args estilo curl: -H 'K: V' e -d '...'
args = sys.argv[1:]
i = 0
while i < len(args):
    a = args[i]
    if a in ('-H','--header') and i+1 < len(args):
        i += 1
        h = args[i]
        # suporte a headerfile: @/tmp/...
        if h.startswith('@'):
            path = h[1:]
            try:
                txt = open(path,'r',encoding='utf-8').read().strip()
                if txt.lower().startswith('authorization:'):
                    headers['Authorization'] = txt.split(':',1)[1].strip()
            except FileNotFoundError:
                pass
        else:
            if ':' in h:
                k,v = h.split(':',1)
                headers[k.strip()] = v.strip()
    elif a in ('-d','--data','--data-raw','--data-binary') and i+1 < len(args):
        i += 1
        data = args[i].encode('utf-8')
        headers.setdefault('Content-Type','application/json')
    i += 1

# se não veio Authorization, tenta do header padrão do smoke
if 'Authorization' not in headers and hdr_file:
    try:
        txt = open(hdr_file,'r',encoding='utf-8').read().strip()
        if txt.lower().startswith('authorization:'):
            headers['Authorization'] = txt.split(':',1)[1].strip()
    except FileNotFoundError:
        pass

req = urllib.request.Request(url, data=data, headers=headers, method=method)
status = 0
body = ''
try:
    with urllib.request.urlopen(req, timeout=timeout) as r:
        status = r.status
        body = r.read().decode('utf-8')
except HTTPError as e:
    status = e.code
    body = e.read().decode('utf-8') if hasattr(e,'read') else ''

open(out,'w',encoding='utf-8').write(body)

if not (200 <= status < 300):
    print(f'❌ HTTP {status} {method} {url}')
    try:
        print(json.dumps(json.loads(body), indent=2, ensure_ascii=False))
    except Exception:
        print(body)
    raise SystemExit(1)

try:
    json.loads(body)
except Exception as e:
    print(f'❌ JSON inválido {method} {url}: {e}')
    print(body)
    raise SystemExit(1)

print('OK')
PY_REQ
  return $?
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

  id_out="${TMPDIR:-/tmp}/ia-cnpj_company_id_$$.out"
  hdr_out="/tmp/ia_cnpj_auth_header"

  ID_OUT="$id_out" HDR_OUT="$hdr_out" python - <<'PY_COMPANY'
import json, os, urllib.request
from urllib.error import HTTPError

base = os.environ.get("BASE", "http://127.0.0.1:8100").rstrip("/")
prefix = os.environ.get("API_PREFIX", "")
cid = int(os.environ.get("COMPANY_ID", "1"))
cnpj = os.environ.get("SMOKE_CNPJ", "12345678000195")
razao = os.environ.get("SMOKE_RAZAO", "__SMOKE_COMPANY__ LTDA")
id_out = os.environ.get("ID_OUT", "/tmp/ia-cnpj_company_id.out")
hdr_out = os.environ.get("HDR_OUT", "/tmp/ia_cnpj_auth_header")

def read_auth_header_file(path: str):
    try:
        txt = open(path, "r", encoding="utf-8").read().strip()
        if txt.lower().startswith("authorization:"):
            val = txt.split(":", 1)[1].strip()
            if val.lower().startswith("bearer ") and len(val) > 20:
                return val
    except FileNotFoundError:
        return None
    return None

def login_get_token():
    user = os.getenv("SMOKE_AUTH_USER") or os.getenv("AUTH_USERNAME") or "dev"
    pw = os.getenv("SMOKE_AUTH_PASS") or os.getenv("AUTH_PASSWORD") or os.getenv("AUTH_PLAIN_PASSWORD") or "dev"
    payload = json.dumps({"username": user, "password": pw}).encode("utf-8")

    for login_url in (f"{base}{prefix}/auth/login", f"{base}/auth/login"):
        try:
            req = urllib.request.Request(login_url, data=payload, headers={"Content-Type":"application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=15) as r:
                body = r.read().decode("utf-8")
            tok = json.loads(body).get("access_token")
            if tok:
                # grava header para o bash reutilizar
                open(hdr_out, "w", encoding="utf-8").write(f"Authorization: Bearer {tok}")
                return f"Bearer {tok}"
        except HTTPError:
            pass
        except Exception:
            pass
    return None

def req(method, url, payload=None, auth=None, timeout=10):
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if auth:
        headers["Authorization"] = auth
    r = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
            return resp.status, body
    except HTTPError as e:
        body = e.read().decode("utf-8") if hasattr(e, "read") else ""
        return e.code, body

# tenta usar header já existente (se alguém já gerou)
auth = read_auth_header_file(hdr_out)

def get_company_by_id(auth_val):
    for url in (f"{base}/companies/{cid}", f"{base}/api/v1/companies/{cid}"):
        code, body = req("GET", url, None, auth=auth_val, timeout=8)
        if code == 200:
            Path = __import__("pathlib").Path
            Path(id_out).write_text(str(cid), encoding="utf-8")
            return True
        if code == 401 and ("Missing bearer token" in body or "Unauthorized" in body or body):
            return (401, url, body)
        if code not in (404, 401):
            raise SystemExit(f"FAIL preflight get company http={code} url={url} body={body[:200]}")
    return False

res = get_company_by_id(auth)
if res is True:
    raise SystemExit(0)

if isinstance(res, tuple) and res[0] == 401 and (not auth or "token expired" in (res[2] or "").lower()):
    # auth necessário -> faz login e retry
    auth = login_get_token()
    if not auth:
        raise SystemExit(f"FAIL preflight auth: /companies exige token e login falhou")
    res2 = get_company_by_id(auth)
    if res2 is True:
        raise SystemExit(0)

# se não existe por id, tenta seed (com auth se necessário)
payload = {"cnpj": cnpj, "razao_social": razao}
seed_urls = (f"{base}/companies", f"{base}/api/v1/companies")
seed_code = None
seed_body = ""
used_seed_url = None
for u in seed_urls:
    code, body = req("POST", u, payload, auth=auth, timeout=12)
    used_seed_url = u
    seed_code, seed_body = code, body
    if code == 401 and (not auth or "token expired" in (body or "").lower()):
        auth = login_get_token()
        if not auth:
            raise SystemExit("FAIL preflight auth: seed exige token e login falhou")
        code, body = req("POST", u, payload, auth=auth, timeout=12)
        seed_code, seed_body = code, body
    if code != 404:
        break

if seed_code not in (200, 201, 409):
    raise SystemExit(f"FAIL preflight seed http={seed_code} url={used_seed_url} body={seed_body[:200]}")

if seed_code in (200, 201):
    try:
        obj = json.loads(seed_body)
        new_id = obj.get("id") or obj.get("company_id")
        if new_id:
            cid = int(new_id)
    except Exception:
        pass
    __import__("pathlib").Path(id_out).write_text(str(cid), encoding="utf-8")
    raise SystemExit(0)

# 409: já existe -> lista e acha pelo cnpj
for u in (used_seed_url, f"{base}/api/v1/companies", f"{base}/companies"):
    if not u:
        continue
    code, body = req("GET", u, None, auth=auth, timeout=12)
    if code == 401 and (not auth or "token expired" in (body or "").lower()):
        auth = login_get_token()
        if not auth:
            continue
        code, body = req("GET", u, None, auth=auth, timeout=12)
    if code != 200:
        continue
    try:
        data = json.loads(body)
    except Exception:
        continue
    items = data
    if isinstance(data, dict):
        items = data.get("items") or data.get("data") or data
    found = None
    if isinstance(items, list):
        for it in items:
            if isinstance(it, dict) and it.get("cnpj") == cnpj and it.get("id") is not None:
                found = it.get("id")
                break
    elif isinstance(items, dict) and items.get("cnpj") == cnpj and items.get("id") is not None:
        found = items.get("id")
    if found:
        __import__("pathlib").Path(id_out).write_text(str(int(found)), encoding="utf-8")
        raise SystemExit(0)

raise SystemExit("FAIL preflight: não consegui determinar COMPANY_ID")
PY_COMPANY

  # se o python gerou header, ativa auth pro resto do smoke
  if [ -s "$hdr_out" ]; then
    __hdr="$hdr_out"
    CURL_AUTH=(-H "@$__hdr")
    echo "ℹ️ preflight: auth header ativado (__hdr=$__hdr)"
  fi

  if [ ! -s "$id_out" ]; then
    echo "❌ preflight: não consegui determinar COMPANY_ID"
    return 1
  fi

  read -r COMPANY_ID < "$id_out" || true
  if [[ -z "$COMPANY_ID" || ! "$COMPANY_ID" =~ ^[0-9]+$ ]]; then
    echo "❌ preflight: COMPANY_ID inválido após python: $COMPANY_ID"
    return 1
  fi

  echo "ℹ️ preflight: usando COMPANY_ID=$COMPANY_ID"
  return 0
}

echo "== IA-CNPJ SMOKE =="
echo "BASE=$BASE COMPANY_ID=$COMPANY_ID START=$START END=$END"
step 1 "/health"

# workaround: em alguns ambientes, bash+cURL -w/%{http_code} tem causado segfault.
# Faz checagem determinística via Python (HTTP 200 + JSON parse).
python - <<'PY_HEALTH'
import json, os, urllib.request

base = os.environ.get("BASE", "http://127.0.0.1:8100").rstrip("/")
url = f"{base}/health"

req = urllib.request.Request(url, method="GET")
with urllib.request.urlopen(req, timeout=10) as r:
    body = r.read().decode("utf-8")
    if r.status != 200:
        raise SystemExit(f"FAIL health http={r.status}")
try:
    json.loads(body)
except Exception as e:
    raise SystemExit(f"FAIL health json: {e}")
print("OK")
PY_HEALTH
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

# valida: HTTP 200 + JSON + contrato (shape + caps) sem segfault do bash
out="/tmp/smoke_11_ai_consult.json"
req_json 20 POST "$BASE_API/ai/consult" "$out" \
  -H "Content-Type: application/json" \
  -d "{\"company_id\":$COMPANY_ID,\"start\":\"$START\",\"end\":\"$END\",\"limit\":10,\"question\":\"smoke\"}" \
  || fail "step 11 falhou"

COMPANY_ID="$COMPANY_ID" START="$START" END="$END" python - <<'PY_CONTRACT'
import json, os

path = "/tmp/smoke_11_ai_consult.json"
obj = json.load(open(path, "r", encoding="utf-8"))

def fail(msg):
    raise SystemExit("FAIL contract: " + msg)

if not isinstance(obj, dict):
    fail("root não é objeto")

cid = int(os.environ.get("COMPANY_ID", "1"))
start = os.environ.get("START", "")
end = os.environ.get("END", "")

# shape mínimo
if "company_id" not in obj:
    fail("faltou company_id")
if int(obj.get("company_id")) != cid:
    fail(f"company_id mismatch: got={obj.get('company_id')} expected={cid}")

period = obj.get("period")
if not isinstance(period, dict):
    fail("faltou period{start,end}")
if period.get("start") != start:
    fail(f"period.start mismatch: got={period.get('start')} expected={start}")
if period.get("end") != end:
    fail(f"period.end mismatch: got={period.get('end')} expected={end}")

# caps
rt = obj.get("recent_transactions")
if rt is None:
    fail("faltou recent_transactions")
if not isinstance(rt, list):
    fail("recent_transactions não é lista")
if len(rt) > 20:
    fail(f"recent_transactions > 20 (len={len(rt)})")

import os as _os
sz = _os.path.getsize(path)
if sz > 350_000:
    fail(f"payload muito grande: {sz} bytes")

print("[contract] /ai/consult shape + caps OK")
PY_CONTRACT

echo "OK"

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
