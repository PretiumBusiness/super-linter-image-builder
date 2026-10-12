.DEFAULT_GOAL := help

.PHONY: help check-env install dev test lint format type-check build clean

SHELL := /usr/bin/env bash
.SHELLFLAGS := -eu -o pipefail -c
UV ?= uv

help:
	@echo "Available commands:"
	@echo "  install     - Install the package with dev dependencies (uv sync)"
	@echo "  test        - Run pytest"
	@echo "  lint        - Run ruff check"
	@echo "  format      - Run ruff format"
	@echo "  type-check  - Run mypy"
	@echo "  build       - Build sdist and wheel into dist/"
	@echo "  clean       - Remove build and test artifacts"

check-env:
	@command -v $(UV) >/dev/null 2>&1 || { echo "uv not found; install it: https://docs.astral.sh/uv/getting-started/installation/"; exit 1; }

install: check-env
	@$(UV) sync

dev: install

test: install
	@$(UV) run pytest

lint: install
	@$(UV) run ruff check src/ tests/

format: install
	@$(UV) run ruff format src/ tests/

type-check: install
	@$(UV) run mypy src/

build: clean check-env
	@$(UV) build

clean:
	@rm -rf dist/ .pytest_cache/ .mypy_cache/ .ruff_cache/ .coverage coverage.xml
	@find . -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true
