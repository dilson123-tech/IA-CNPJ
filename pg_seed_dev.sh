#!/usr/bin/env bash
set -euo pipefail

# 1) Garante Postgres dev rodando (porta 55532)
./pg_local_up.sh

# 2) Aponta o backend pro Postgres dev
export DATABASE_URL="postgresql://ia_cnpj:ia_cnpj@localhost:55532/ia_cnpj"

# 3) Força IA_CNPJ_ENV=lab só para reaproveitar o seed existente
export IA_CNPJ_ENV="lab"

echo "🔌 DATABASE_URL = $DATABASE_URL"
echo "🌱 IA_CNPJ_ENV   = $IA_CNPJ_ENV"
echo

# 4) Entra na pasta backend e roda o seed via Python inline
cd backend

python - << 'PY'
from app.db import SessionLocal
from app.api.auth import _lab_seed_if_needed

print("🌱 Rodando _lab_seed_if_needed no Postgres dev...")

db = SessionLocal()
try:
    _lab_seed_if_needed(db)
    db.commit()
    print("✅ Seed dev aplicado (ou dados já existiam).")
finally:
    db.close()
PY
