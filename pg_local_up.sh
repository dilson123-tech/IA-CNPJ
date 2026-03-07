#!/usr/bin/env bash
set -euo pipefail

PORT=55532
CONTAINER="ia-cnpj-pg"
VOLUME="ia_cnpj_pg_data"

echo "🧹 Limpando container antigo (se existir)..."
docker rm -f "$CONTAINER" >/dev/null 2>&1 || true

echo "🧹 Garantindo volume..."
docker volume create "$VOLUME" >/dev/null 2>&1 || true

echo "🚀 Subindo Postgres dev ($CONTAINER) na porta $PORT..."
docker run -d \
  --name "$CONTAINER" \
  -e POSTGRES_DB=ia_cnpj \
  -e POSTGRES_USER=ia_cnpj \
  -e POSTGRES_PASSWORD=ia_cnpj \
  -p "${PORT}:5432" \
  -v "${VOLUME}:/var/lib/postgresql/data" \
  postgres:16

echo "⏳ Aguardando Postgres responder..."
for i in {1..40}; do
  if docker exec "$CONTAINER" pg_isready -U ia_cnpj -d ia_cnpj >/dev/null 2>&1; then
    echo "✅ Postgres está saudável."
    break
  fi
  sleep 2
done

if ! docker exec "$CONTAINER" pg_isready -U ia_cnpj -d ia_cnpj >/dev/null 2>&1; then
  echo "⚠️ Timeout esperando Postgres ficar pronto."
  echo "   Veja logs com: docker logs $CONTAINER"
  exit 1
fi

echo
echo "📌 Postgres dev pronto:"
echo "   Host:     localhost"
echo "   Porta:    ${PORT}"
echo "   Banco:    ia_cnpj"
echo "   Usuário:  ia_cnpj"
echo "   Senha:    ia_cnpj"
echo
echo "🔐 URL de conexão:"
echo "   postgresql://ia_cnpj:ia_cnpj@localhost:${PORT}/ia_cnpj"
echo
echo "💡 Exemplos de uso:"
echo
echo "   # Rodar app apontando pro Postgres dev"
echo "   cd backend && \\"
echo "   DATABASE_URL=\"postgresql://ia_cnpj:ia_cnpj@localhost:${PORT}/ia_cnpj\" \\"
echo "   uvicorn app.main:app --reload"
echo
echo "   # Rodar testes em Postgres (quando fizer sentido) com opt-in explícito:"
echo "   cd backend && \\"
echo "   DATABASE_URL=\"postgresql://ia_cnpj:ia_cnpj@localhost:${PORT}/ia_cnpj\" \\"
echo "   IA_CNPJ_ALLOW_PG_TESTS=true \\"
echo "   python -m pytest -q"
