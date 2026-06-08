.PHONY: dev test lint type check fix all
.DEFAULT_GOAL := check

# Run the dev server, watching src/ and .env from anywhere
run:
	uv run uvicorn flash.main:app --reload --reload-dir src --reload-include .env

# Run the test suite
test:
	uv run pytest

# Lint with ruff
lint:
	uv run ruff check .

# Auto-fix lint issues + format
fix:
	uv run ruff check --fix .
	uv run ruff format .

# Type-check
type:
	uv run mypy src

# Run everything (what CI / pre-push would do)
check: lint type test