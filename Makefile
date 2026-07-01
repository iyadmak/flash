.PHONY: dev test lint type check fix all
.DEFAULT_GOAL := check

# Run the dev server, watching src/ and .env from anywhere
run:
	docker run -p 8000:8000 --env-file .env flash:dev

up-dev:
	docker compose up -d

up-prod:
	docker compose -f docker-compose.yaml -f docker-compose.prod.yaml up -d

build-dev:
	docker compose up --build

build-prod:
	docker compose -f docker-compose.yaml -f docker-compose.prod.yaml up --build

down:
	docker compose down

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
	uv run mypy .

# Run everything (what CI / pre-push would do)
check: lint type test