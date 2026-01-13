SHELL := /usr/bin/env bash
.SHELLFLAGS := -eu -o pipefail -c

PORT ?= 8100
HOST ?= 127.0.0.1
BIND_HOST ?= 0.0.0.0
API_CNPJ ?= http://$\(HOST\):$\(PORT\)

.PHONY: help dev smoke api db

help:
	@echo "Targets:"
	@echo "  make dev        - alembic + sobe API + smoke + encerra (script)"
	@echo "  make smoke      - roda smoke_ai_apply apontando pra API_CNPJ"
	@echo "  make api        - sobe uvicorn (foreground) na PORT"
	@echo "  make db         - alembic upgrade head"
	@echo ""
	@echo "Vars:"
	@echo "  PORT=8100 HOST=127.0.0.1 BIND_HOST=0.0.0.0 API_CNPJ=http://127.0.0.1:8100"

dev:
	PORT=$(PORT) HOST=$(HOST) BIND_HOST=$(BIND_HOST) ./backend/scripts/dev_up_smoke.sh

smoke:
	API_CNPJ="$(API_CNPJ)" ./backend/scripts/smoke_ai_apply.sh

api:
	cd backend && source .venv/bin/activate && uvicorn app.main:app --host $(BIND_HOST) --port $(PORT) --reload

db:
	cd backend && source .venv/bin/activate && alembic upgrade head
