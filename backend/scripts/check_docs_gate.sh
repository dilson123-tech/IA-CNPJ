#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8100}"

health="$(curl -sS --max-time 3 "$BASE_URL/health")"

# Extrai flags sem depender de jq (mas usa jq se existir)
if command -v jq >/dev/null 2>&1; then
  env="$(printf '%s' "$health" | jq -r '.env')"
  auth_enabled="$(printf '%s' "$health" | jq -r '.auth_enabled')"
  docs_protected="$(printf '%s' "$health" | jq -r '.docs_protected')"
else
  env="$(printf '%s' "$health" | sed -n 's/.*"env"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')"
  auth_enabled="$(printf '%s' "$health" | sed -n 's/.*"auth_enabled"[[:space:]]*:[[:space:]]*\([^,}]*\).*/\1/p')"
  docs_protected="$(printf '%s' "$health" | sed -n 's/.*"docs_protected"[[:space:]]*:[[:space:]]*\([^,}]*\).*/\1/p')"
fi

echo "[gate] BASE_URL=$BASE_URL env=$env auth_enabled=$auth_enabled docs_protected=$docs_protected"

check() {
  local path="$1" expect="$2"
  local code
  code="$(curl -sS -o /dev/null -w "%{http_code}" --max-time 3 "$BASE_URL$path" || true)"
  if [[ "$code" != "$expect" ]]; then
    echo "❌ $path expected=$expect got=$code"
    exit 1
  fi
  echo "✅ $path $code"
}

# /health sempre 200
check "/health" "200"

# docs/openapi: 401 quando docs_protected=true, senão 200
if [[ "$docs_protected" == "true" ]]; then
  check "/docs" "401"
  check "/redoc" "401"
  check "/openapi.json" "401"
else
  check "/docs" "200"
  check "/redoc" "200"
  check "/openapi.json" "200"
fi

echo "✅ DOCS GATE OK"
