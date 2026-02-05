SHELL := /usr/bin/env bash
.SHELLFLAGS := -eu -o pipefail -c

BACKEND ?= backend
VENV ?= $(BACKEND)/.venv
PY_SYS ?= python3

PY ?= $(VENV)/bin/python
PIP ?= $(VENV)/bin/pip

PORT ?= 8100
HOST ?= 127.0.0.1
BIND_HOST ?= 0.0.0.0
API_CNPJ ?= http://$(HOST):$(PORT)

REQ ?= $(BACKEND)/requirements.txt

.PHONY: api db dev help lint smoke venv

help:
	@echo "Targets:"
	@echo "  make venv       - cria venv + instala deps (backend/requirements.txt)"
	@echo "  make dev        - alembic + sobe API + smoke + encerra (script)"
	@echo "  make smoke      - roda smoke_ai_apply apontando pra API_CNPJ"
	@echo "  make api        - sobe uvicorn (foreground) na PORT" --loop asyncio --http h11
	@echo "  make db         - alembic upgrade head"
	@echo ""
	@echo "Vars:"
	@echo "  PORT=8100 HOST=127.0.0.1 BIND_HOST=0.0.0.0 API_CNPJ=http://127.0.0.1:8100"

venv:
	@test -f "$(REQ)" || (echo "❌ faltou $(REQ). Commitou esse arquivo?" >&2; exit 1)
	@if [ ! -x "$(PY)" ]; then \
	  echo "== criando venv em $(VENV) =="; \
	  $(PY_SYS) -m venv "$(VENV)"; \
	fi
	@"$(PIP)" install --upgrade pip
	@"$(PIP)" install -r "$(REQ)"
	@if [ -f "$(BACKEND)/requirements-dev.txt" ]; then \
	  echo "== instalando deps dev =="; \
	  "$(PIP)" install -r "$(BACKEND)/requirements-dev.txt"; \
	fi

dev: venv
	PORT=$(PORT) HOST=$(HOST) BIND_HOST=$(BIND_HOST) ./backend/scripts/dev_up_smoke.sh

smoke:
	API_CNPJ="$(API_CNPJ)" ./backend/scripts/smoke_ai_apply.sh

api: venv
	cd $(BACKEND) && source .venv/bin/activate && uvicorn app.main:app --host $(BIND_HOST) --port $(PORT) --reload

db: venv
	cd $(BACKEND) && source .venv/bin/activate && alembic upgrade head


lint: venv
	cd $(BACKEND) && source .venv/bin/activate && ruff check .
	cd $(BACKEND) && source .venv/bin/activate && python -m compileall -q .
	cd $(BACKEND) && find scripts -type f -name '*.sh' -print0 | xargs -0 -r -n1 bash -n
