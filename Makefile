# Console de supervision Dialeo (Diallo-sup) — raccourcis de developpement.
.DEFAULT_GOAL := help
PY := .venv/bin/python
PIP := .venv/bin/pip

.PHONY: help install dev test lint front-install front-dev front-build front-test front-lint

help: ## Affiche cette aide
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "} {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

install: ## Cree le venv si absent puis installe les dependances backend (+ dev)
	test -d .venv || python3.13 -m venv .venv
	$(PIP) install -e ".[dev]"

dev: ## Lance le backend FastAPI (uvicorn, rechargement a chaud, :8000)
	$(PY) -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

test: ## Lance la suite de tests backend (pytest)
	$(PY) -m pytest

lint: ## Verifie le style backend avec ruff
	$(PY) -m ruff check .

front-install: ## Installe les dependances du frontend (npm)
	cd frontend && npm install

front-dev: ## Lance le serveur de dev Vite (:5173, proxy /api,/health -> :8000)
	cd frontend && npm run dev

front-build: ## Build le SPA dans frontend/dist (servi ensuite par FastAPI)
	cd frontend && npm run build

front-test: ## Lance les tests frontend (vitest)
	cd frontend && npm run test

front-lint: ## Verifie le style frontend (eslint)
	cd frontend && npm run lint
