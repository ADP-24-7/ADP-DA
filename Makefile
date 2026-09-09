SHELL := bash

VENV := .venv
NCP_ENV ?= .env.ncp.local
COMPOSE ?= docker compose --project-directory ../ADP-BE -f ../ADP-BE/docker-compose.yml -f $(CURDIR)/docker-compose.yml

ifeq ($(OS),Windows_NT)
PYTHON ?= py -3.12
BIN := $(VENV)/Scripts
PY := $(BIN)/python.exe
VENV_READY := $(BIN)/activate
else
PYTHON ?= python3.12
BIN := $(VENV)/bin
PY := $(BIN)/python
VENV_READY := $(BIN)/activate
endif

PIP := $(PY) -m pip

.DEFAULT_GOAL := help

.PHONY: help setup install install-dev env be-env ncp-storage-env test lint format typecheck contract-check check ai-eval-preflight ai-eval-consume ai-eval-e2e ncp-storage-preflight ncp-storage-e2e docker-network docker-build docker-up docker-rebuild docker-down docker-logs docker-ps clean

help:
	@echo "ADP-DA commands"
	@echo ""
	@echo "  make setup          Create venv, install dev/notebook deps, prepare .env"
	@echo "  make install        Install runtime package"
	@echo "  make install-dev    Install dev and notebook extras"
	@echo "  make test           Run tests"
	@echo "  make lint           Run ruff lint"
	@echo "  make format         Run ruff formatter"
	@echo "  make typecheck      Run mypy"
	@echo "  make contract-check Validate JSON handoff contracts"
	@echo "  make check          Run lint, typecheck, test"
	@echo "  make ai-eval-preflight Check fixed BE-to-DA baseline inputs without network calls"
	@echo "  make ai-eval-consume   Validate readiness and analyze an existing BE Bundle"
	@echo "  make ai-eval-e2e     Run guarded real 3-model BE-to-DA evaluation"
	@echo "  make ncp-storage-preflight Check NCP storage settings without network calls"
	@echo "  make ncp-storage-e2e Run opt-in NCP upload/download/digest/cleanup drill"
	@echo "  make docker-up      Start BE, FE, DA, Docs and PostgreSQL dev stack"
	@echo "  make docker-rebuild Rebuild and start the full dev stack"
	@echo "  make docker-down    Stop full dev stack"
	@echo "  make docker-logs    Follow full dev stack logs"
	@echo "  make docker-ps      Show full dev stack containers"
	@echo "  make clean          Remove local caches"

setup: $(VENV_READY) install-dev env

$(VENV_READY):
	$(PYTHON) -m venv $(VENV)

install: $(VENV_READY)
	$(PIP) install --upgrade pip
	$(PIP) install -e .

install-dev: $(VENV_READY)
	$(PIP) install --upgrade pip
	$(PIP) install -e ".[dev,notebook]"

env:
	@if [ ! -f .env ]; then cp .env.example .env; fi

be-env:
	@if [ ! -f ../ADP-BE/.env ]; then cp ../ADP-BE/.env.example ../ADP-BE/.env; fi

ncp-storage-env:
	@if [ ! -f $(NCP_ENV) ]; then cp .env.ncp.local.example $(NCP_ENV); chmod 600 $(NCP_ENV); fi

test:
	$(PY) -m pytest

lint:
	$(PY) -m ruff check .

format:
	$(PY) -m ruff format .

typecheck:
	$(PY) -m mypy 02_ai/src

contract-check:
	$(PY) scripts/validate_contracts.py

check: lint typecheck contract-check test

ai-eval-preflight:
	$(PY) -m adp_da.evaluation_e2e

ai-eval-consume:
	$(PY) -m adp_da.evaluation_e2e --consume-existing

ai-eval-e2e:
	$(PY) -m adp_da.evaluation_e2e --execute

ncp-storage-preflight:
	@set -a; if [ -f $(NCP_ENV) ]; then . $(NCP_ENV); fi; set +a; \
	ADP_CODE_GIT_SHA="$$(git rev-parse HEAD)" $(PY) -m adp_da.ncp_storage_e2e

ncp-storage-e2e:
	@test -f $(NCP_ENV) || (echo "Missing $(NCP_ENV); run make ncp-storage-env"; exit 1)
	@set -a; . $(NCP_ENV); set +a; \
	ADP_CODE_GIT_SHA="$$(git rev-parse HEAD)" $(PY) -m adp_da.ncp_storage_e2e --execute

docker-network:
	@docker network inspect adp-local >/dev/null 2>&1 || docker network create adp-local

docker-build:
	$(COMPOSE) build

docker-up: env be-env docker-network
	$(COMPOSE) up -d --build

docker-rebuild: env be-env docker-network
	$(COMPOSE) build --no-cache
	$(COMPOSE) up -d

docker-down:
	$(COMPOSE) down

docker-logs:
	$(COMPOSE) logs -f

docker-ps:
	$(COMPOSE) ps

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache .pycache
	find . -type d -name "__pycache__" -prune -exec rm -rf {} +
