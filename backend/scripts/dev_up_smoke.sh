#!/usr/bin/env bash
set -euo pipefail
# --- DB consistente (CI-safe): caminho absoluto p/ SQLite ---
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DB_PATH="${DB_PATH:-$ROOT/backend/lab.db}"
export DATABASE_URL="${DATABASE_URL:-sqlite:///${DB_PATH}}"
echo "[db] DATABASE_URL=$DATABASE_URL"


# raiz do repo (../.. a partir de backend/scripts)
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"


# DB consistente (evita alembic migrar um sqlite e a API subir em outro)
DB_PATH="${DB_PATH:-$ROOT/backend/app.db}"


ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
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
echo "[2/4] subindo uvicorn em ${BIND_HOST}:${PORT} (bg) | log: ${LOG}"
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
