.PHONY: setup up db-up down stack dev migrate migrations test lint format typecheck check backup restore-rehearsal

setup:
	uv sync

up:
	docker compose up -d --build

db-up:
	docker compose up -d db

down:
	docker compose down

stack:
	docker compose up --build

dev:
	uv run python manage.py runserver

migrate:
	uv run python manage.py migrate

migrations:
	uv run python manage.py makemigrations

test:
	uv run pytest

lint:
	uv run ruff check .

format:
	uv run ruff format .

typecheck:
	uv run pyright

check: lint typecheck test

backup:
	scripts/postgres-backup.sh

restore-rehearsal:
	scripts/postgres-restore-rehearsal.sh
