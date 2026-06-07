.PHONY: up down serve app frontend frontend-install migrate migrate-down revision ingest index eval test lint fmt check-providers check-ingest check-index check-retrieval check-generation install

install:
	pip install -e ".[dev]"

up:
	docker compose up -d --build

down:
	docker compose down

serve:
	uvicorn citely.api.app:create_app --factory --host 0.0.0.0 --port 8000 --reload

frontend-install:
	cd frontend && npm install

frontend:
	cd frontend && npm run dev

# Launch the whole app for local dev: Postgres (docker), the FastAPI API on :8000, and the
# Vite frontend on :5173 (proxies /search,/review,/ingest,/health -> :8000). Requires a
# host Ollama running for the default provider. Ctrl-C stops everything.
app:
	@echo "==> Citely: starting Postgres (docker), API :8000, frontend :5173"
	docker compose up -d --wait db
	alembic upgrade head
	@[ -d frontend/node_modules ] || (cd frontend && npm install)
	@trap 'kill 0' INT TERM EXIT; \
		uvicorn citely.api.app:create_app --factory --host 0.0.0.0 --port 8000 & \
		( cd frontend && npm run dev ) & \
		wait

migrate:
	alembic upgrade head

migrate-down:
	alembic downgrade -1

revision:
	alembic revision -m "$(m)"

ingest:
	python -m citely.ingest --categories 'cs.*' 'eess.*' --max 50000

index:
	python -m citely.indexing

eval:
	python -m citely.eval

test:
	pytest

lint:
	ruff check citely tests scripts
	mypy citely

fmt:
	ruff check --fix citely tests scripts
	ruff format citely tests scripts

check-providers:
	python scripts/check_providers.py

check-ingest:
	python scripts/check_ingest.py

check-index:
	python scripts/check_index.py

check-retrieval:
	python scripts/check_retrieval.py

check-generation:
	python scripts/check_generation.py
