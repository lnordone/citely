.PHONY: up down ingest eval test lint fmt check-providers install

install:
	pip install -e ".[dev]"

up:
	docker compose up -d --build

down:
	docker compose down

ingest:
	python -m citely.ingest --categories cs.AI cs.LG cs.CL --max 50000

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
