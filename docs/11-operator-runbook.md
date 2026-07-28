# Local operator runbook

## Scope

This runbook covers local foundation operation only. It does not authorize
production deployment, customer data, external integrations, or product-specific
automation while the validation gate remains open.

## Prerequisites

- Python 3.12.3 selected through pyenv;
- `uv` available;
- Docker Desktop running; and
- repository working directory at `/Users/cpg24/Development/codex/autobiz`.

## First setup

```bash
cp .env.example .env
make setup
make up
```

Do not place production credentials or customer data in `.env`.

## Daily local operation

Start the complete containerized stack in the background:

```bash
make up
```

For direct Django development, start only PostgreSQL and then the development server:

```bash
make db-up
make dev
```

Or run the containerized stack:

```bash
make stack
```

Verify:

```bash
curl -fsS http://127.0.0.1:8000/health/
curl -fsS http://127.0.0.1:8000/ready/
```

- `/health/` proves that the web process can respond.
- `/ready/` proves that the web process can query its configured database.

Stop containers without deleting the PostgreSQL volume:

```bash
make down
```

## Quality checks

Preferred:

```bash
make check
```

If the sandbox prevents uv from accessing its shared cache, run the already
installed tools directly:

```bash
.venv/bin/ruff check .
.venv/bin/pyright
.venv/bin/pytest -q
.venv/bin/python manage.py check
.venv/bin/python manage.py makemigrations --check --dry-run
```

## PostgreSQL-backed tests

With PostgreSQL running:

```bash
env \
  DB_HOST=127.0.0.1 \
  DB_PORT=5432 \
  DB_NAME=autobiz \
  DB_USER=autobiz \
  DB_PASSWORD=autobiz-local-only \
  .venv/bin/pytest -q
```

The test runner creates and removes its own test database.

## Migrations

Create a migration only after an intentional model change:

```bash
make migrations
```

Review the migration, then apply it:

```bash
make migrate
```

Never edit an already-applied migration to change production behavior.

## Backup and restore rehearsal

Start PostgreSQL and apply migrations before taking a backup:

```bash
make db-up
make migrate
make backup
make restore-rehearsal
```

Backups are written under ignored `backups/local/`. The rehearsal restores into the
fixed scratch database `autobiz_restore_check`, verifies migration records, and
drops only that scratch database when complete. It does not overwrite `autobiz`.

## Logs and correlation

Application logs are JSON. Every HTTP response includes `X-Request-ID`; a safe
incoming ID is preserved and an unsafe/missing ID is replaced. Request logs contain
method, path, status, duration, and request ID, but not query strings, request
bodies, model inputs, credentials, or customer payloads.

## Common failures

### Docker socket unavailable

Start Docker Desktop, wait for `docker info` to succeed, then rerun `make up`.

### PostgreSQL connection denied by sandbox

The local database connection may require a scoped approval for `127.0.0.1:5432`.
Do not weaken database authentication or expose the database beyond localhost.

### Readiness returns 503

Check:

```bash
docker compose ps
docker compose logs db
docker compose logs web
```

Confirm database variables match `.env`, the database is healthy, and migrations
have been applied.

### Migration drift

If `makemigrations --check --dry-run` reports changes, create and review the
migration. Do not suppress the check.

## Recovery and escalation

For local disposable state, stop the stack and diagnose before changing data. Do
not remove volumes as a routine fix. For any future production incident involving
customer data, unauthorized actions, or financial impact, stop the affected
automation and follow the severity rules in `docs/07-controls-and-risks.md`.

## Validation boundary

Before adding an AI workflow, customer-system integration, firm offer, or
production deployment, read `docs/09-required-validation-gate.md`. If the gate is
still open, stop and resume customer validation.
