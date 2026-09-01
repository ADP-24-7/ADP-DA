SHELL := bash

VENV := .venv
COMPOSE ?= docker compose

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

.PHONY: help setup install install-dev env test lint format typecheck contract-check check docker-network docker-build docker-up docker-rebuild docker-down docker-logs docker-ps clean

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

test:
	$(PY) -m pytest

lint:
	$(PY) -m ruff check .

format:
	$(PY) -m ruff format .

typecheck:
	$(PY) -m mypy src

contract-check:
	$(PY) scripts/validate_contracts.py

check: lint typecheck contract-check test

docker-network:
	@docker network inspect adp-local >/dev/null 2>&1 || docker network create adp-local

docker-build:
	$(COMPOSE) build

docker-up: env docker-network
	$(COMPOSE) up -d --build

docker-rebuild: env docker-network
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
