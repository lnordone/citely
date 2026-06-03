.PHONY: up down migrate migrate-down revision ingest index eval test lint fmt check-providers check-ingest check-index check-retrieval check-generation install

install:
	pip install -e ".[dev]"

up:
	docker compose up -d --build

down:
	docker compose down

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
