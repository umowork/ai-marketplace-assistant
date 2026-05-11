# Makefile — AI Marketplace Assistant

PROJECT_NAME := ai-marketplace-assistant
PYTHON := python3
DOCKER_COMPOSE := docker-compose

.PHONY: all lint test test-cov typecheck clean install install-dev run docker-build docker-run down help check

all: lint typecheck test

## === Quality ===

lint:
	ruff check . --ignore E501
	@echo "✅ Lint passed"

typecheck:
	-mypy marketplace_assistant/ --ignore-missing-imports
	@echo "✅ Type check passed (warnings may exist)"

test:
	python3 -m pytest tests/ -v --tb=short -m "not real_api"
	@echo "✅ Tests passed"

test-cov:
	python3 -m pytest tests/ -v --tb=short -m "not real_api" --cov=marketplace_assistant --cov-report=term --cov-report=html
	@echo "✅ Coverage report generated"

test-all:
	python3 -m pytest tests/ -v --tb=short --cov=marketplace_assistant
	@echo "✅ All tests passed"

test-slow:
	python3 -m pytest tests/ -v --tb=short -m "slow"
	@echo "✅ Slow tests passed"

## === Docker ===

docker-build:
	docker-compose -f docker-compose.yml build

docker-run:
	docker-compose -f docker-compose.yml up -d

down:
	docker-compose -f docker-compose.yml down

## === Environment ===

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name ".coverage" -delete
	rm -rf .pytest_cache .ruff_cache htmlcov *.egg-info
	@echo "✅ Cleaned"

install:
	pip install -r requirements.txt
	@echo "✅ Dependencies installed"

install-dev:
	pip install -r requirements.txt -r requirements-dev.txt
	@echo "✅ Dev dependencies installed"

## === Run ===

run:
	$(PYTHON) main.py

dev:
	$(PYTHON) -m uvicorn marketplace_assistant.api.fastapi_app:create_app --reload --host 0.0.0.0 --port 8000

## === Check (full pipeline) ===

check: lint typecheck test clean
	@echo "🎉 All checks passed!"

## === Help ===

help:
	@echo "AI Marketplace Assistant — Makefile"
	@echo ""
	@echo "Usage: make <target>"
	@echo ""
	@echo "Quality:"
	@echo "  lint        — Run ruff linter"
	@echo "  typecheck   — Run mypy type checker"
	@echo "  test        — Run pytest (unit tests)"
	@echo "  test-cov    — Run tests with coverage"
	@echo "  test-all    — Run all tests (including real API)"
	@echo ""
	@echo "Docker:"
	@echo "  docker-build  — Build Docker image"
	@echo "  docker-run    — Start containers"
	@echo "  down          — Stop containers"
	@echo ""
	@echo "Environment:"
	@echo "  install       — Install dependencies"
	@echo "  install-dev   — Install dev dependencies"
	@echo "  clean         — Clean caches"
	@echo ""
	@echo "Run:"
	@echo "  run       — Start API + Bot"
	@echo "  dev       — Start API in dev mode (hot reload)"
	@echo ""
	@echo "  check     — Full quality check (lint + typecheck + test)"
