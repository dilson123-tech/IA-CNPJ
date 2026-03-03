#!/usr/bin/env bash
set -euo pipefail
source .venv/bin/activate
unset DATABASE_URL IA_CNPJ_DATABASE_URL
rm -f /tmp/ia_cnpj_test.db
DATABASE_URL="sqlite:////tmp/ia_cnpj_test.db" \
IA_CNPJ_ENV=lab \
IA_CNPJ_AUTH_ENABLED=true \
IA_CNPJ_AUTH_USERNAME=dev \
IA_CNPJ_AUTH_PASSWORD=dev \
IA_CNPJ_AUTH_JWT_SECRET="0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef" \
python -m pytest -q
