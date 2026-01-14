#!/usr/bin/env bash
set -euo pipefail

# --- CI/SMOKE: garante 1 SQLite absoluto (alembic + uvicorn) ---
if [[ -n "${GITHUB_ACTIONS:-}" ]]; then
  ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
  BACKEND_DIR="${ROOT_DIR}/backend"
  CI_DB_PATH="${BACKEND_DIR}/.ci/ci.sqlite"
  mkdir -p "$(dirname "${CI_DB_PATH}")"
  export DATABASE_URL="sqlite:///${CI_DB_PATH}"
  echo "🗄️  CI DATABASE_URL=${DATABASE_URL}"
fi
# --- end CI/SMOKE ---




# --- CI: dump do uvicorn log em qualquer erro ---
dump_uvicorn_log_on_err() {
  if [ "${GITHUB_ACTIONS:-}" = "true" ]; then
    local port="${PORT:-8100}"
    local log="/tmp/ia-cnpj_uvicorn_${port}.log"
    if [ -f "$log" ]; then
      echo ""
      echo "---- tail $log (ultimas 220 linhas) ----"
      tail -n 220 "$log" || true
      echo "---- end ----"
      echo ""
    fi
  fi
}
trap dump_uvicorn_log_on_err ERR
# ----------------------------------------------
# --- CI: DB sqlite unico (alembic + app) ---
if [ "${GITHUB_ACTIONS:-}" = "true" ]; then
  ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
  CI_DB="${IA_CNPJ_CI_DB:-$ROOT_DIR/backend/.ci/ci.sqlite}"
  export DATABASE_URL="sqlite:///${CI_DB}"
  rm -f "${CI_DB}"  # garante estado limpo/idempotente no CI
fi
# -----------------------------------------
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

# --- CI bootstrap: cria venv se não existir (runner não vem com .venv) ---
VENV_ACT="$ROOT/backend/.venv/bin/activate"
if [ ! -f "$VENV_ACT" ]; then
  echo "⚙️  criando venv em $ROOT/backend/.venv (CI)"
  python -m venv "$ROOT/backend/.venv"
  # shellcheck disable=SC1090
  source "$VENV_ACT"
  python -m pip install -U pip
  pip install -r "$ROOT/backend/requirements.txt" -r "$ROOT/backend/requirements-dev.txt"
else
  # shellcheck disable=SC1090
  source "$VENV_ACT"
fi
# ---------------------------------------------------------------------------

BACKEND="$ROOT/backend"
VENV_ACT="$BACKEND/.venv/bin/activate"
ALEMBIC_INI="$BACKEND/alembic.ini"

HOST="${HOST:-127.0.0.1}"
BIND_HOST="${BIND_HOST:-0.0.0.0}"
PORT="${PORT:-8100}"
API_CNPJ="${API_CNPJ:-http://${HOST}:${PORT}}"
UVICORN_APP="${UVICORN_APP:-app.main:app}"

die(){ echo "❌ $*" >&2; exit 1; }

[ -f "$VENV_ACT" ] || die "Venv não encontrada em $VENV_ACT"
[ -f "$ALEMBIC_INI" ] || die "alembic.ini não encontrado em $ALEMBIC_INI"

cd "$BACKEND"
# shellcheck disable=SC1090
source "$VENV_ACT"

if ss -ltnp | grep -qE ":${PORT}\b"; then
  echo "❌ Porta ${PORT} já está em uso:"
  ss -ltnp | grep -E ":${PORT}\b" || true
  echo "Dica: mude a porta com: PORT=8110 $0"
  exit 2
fi

echo "== IA-CNPJ DEV UP + SMOKE =="
echo "API=${API_CNPJ}"

echo "[1/4] alembic upgrade head"
alembic upgrade head

LOG="/tmp/ia-cnpj_uvicorn_${PORT}.log"
env DATABASE_URL="${DATABASE_URL:-}" echo "[2/4] subindo uvicorn em ${BIND_HOST}:${PORT} (bg) | log: ${LOG}"
echo "�� DATABASE_URL=${DATABASE_URL:-<empty>}"
uvicorn "$UVICORN_APP" --host "$BIND_HOST" --port "$PORT" --log-level info >"$LOG" 2>&1 &
UV_PID=$!

cleanup() {
  if kill -0 "$UV_PID" 2>/dev/null; then
    kill -TERM "$UV_PID" 2>/dev/null || true
    wait "$UV_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT

echo "[3/4] aguardando API ficar pronta..."
for i in $(seq 1 60); do
  if curl -sSf --max-time 1 "${API_CNPJ}/openapi.json" >/dev/null 2>/dev/null; then
    echo "OK"
    break
  fi
  if ! kill -0 "$UV_PID" 2>/dev/null; then
    echo "❌ Uvicorn morreu durante o boot. Veja o log: ${LOG}"
    tail -n 120 "$LOG" 2>/dev/null || true
    exit 4
  fi

  sleep 0.25
  if [ "$i" -eq 60 ]; then
    echo "❌ API não subiu a tempo. Veja o log: ${LOG}"
    exit 3
  fi
done

echo "[4/4] smoke_ai_apply"
cd "$ROOT"
API_CNPJ="$API_CNPJ" ./backend/scripts/smoke_ai_apply.sh

echo "✅ DEV UP + SMOKE PASS"
