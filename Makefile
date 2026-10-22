PYTHON ?= python3
VENV   ?= .venv
BIN    := $(VENV)/bin

.DEFAULT_GOAL := help

.PHONY: help install data train setup test lint format serve web build docker clean

help: ## List available targets
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-10s %s\n", $$1, $$2}'

install: ## Create a virtualenv and install backend + frontend dependencies
	$(PYTHON) -m venv $(VENV)
	$(BIN)/pip install -q --upgrade pip
	$(BIN)/pip install -q -e ".[dev]"
	cd frontend && npm ci

data: ## Regenerate the simulated dataset (deterministic, seed 2026)
	$(BIN)/smartcity simulate

train: ## Ingest data into SQLite, train models, write metrics and figures
	$(BIN)/smartcity ingest
	$(BIN)/smartcity train

setup: train ## Everything needed before serving (uses the committed dataset)

test: ## Run the backend test suite
	$(BIN)/pytest

lint: ## Lint and format-check backend and frontend
	$(BIN)/ruff check backend tests
	$(BIN)/ruff format --check backend tests
	cd frontend && npm run lint

format: ## Apply formatting
	$(BIN)/ruff check --fix backend tests
	$(BIN)/ruff format backend tests

serve: ## Run the API on http://127.0.0.1:5000
	$(BIN)/smartcity serve

web: ## Run the dashboard dev server on http://localhost:5173
	cd frontend && npm run dev

build: ## Production build of the dashboard
	cd frontend && npm run build

docker: ## Build and start the full stack
	docker compose up --build

clean: ## Remove generated artefacts
	rm -rf var frontend/dist .pytest_cache .ruff_cache
