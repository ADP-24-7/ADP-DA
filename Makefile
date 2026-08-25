SHELL := bash

VENV := .venv

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

.PHONY: help setup install install-dev env test lint format typecheck check docker-network docker-build docker-up docker-down docker-logs clean

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
	@echo "  make check          Run lint, typecheck, test"
	@echo "  make docker-up      Start local Docker service"
	@echo "  make docker-down    Stop local Docker service"
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

check: lint typecheck test

docker-network:
	@docker network inspect adp-local >/dev/null 2>&1 || docker network create adp-local

docker-build:
	docker compose build

docker-up: docker-network
	docker compose up --build

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache .pycache
	find . -type d -name "__pycache__" -prune -exec rm -rf {} +
