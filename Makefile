# Console de supervision Dialeo (Diallo-sup) — raccourcis de developpement.
.DEFAULT_GOAL := help
PY := .venv/bin/python
PIP := .venv/bin/pip

.PHONY: help install dev test lint

help: ## Affiche cette aide
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "} {printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}'

install: ## Cree le venv si absent puis installe les dependances (+ dev)
	test -d .venv || python3.13 -m venv .venv
	$(PIP) install -e ".[dev]"

dev: ## Lance le serveur de developpement (rechargement a chaud)
	$(PY) -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

test: ## Lance la suite de tests pytest
	$(PY) -m pytest

lint: ## Verifie le style avec ruff
	$(PY) -m ruff check .
