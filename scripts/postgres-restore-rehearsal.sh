#!/bin/sh
set -eu

db_user=${DB_USER:-autobiz}
scratch_db=autobiz_restore_check
backup_path=${1:-}

if [ -z "$backup_path" ]; then
  backup_path=$(find backups/local -type f -name 'autobiz-*.dump' -print | sort | tail -n 1)
fi

if [ -z "$backup_path" ] || [ ! -s "$backup_path" ]; then
  echo "Provide a non-empty Autobiz backup file." >&2
  exit 1
fi

cleanup() {
  docker compose exec -T db dropdb \
    --username "$db_user" \
    --if-exists \
    --force \
    "$scratch_db" >/dev/null
}

trap cleanup EXIT INT TERM
cleanup
docker compose exec -T db createdb --username "$db_user" "$scratch_db"
docker compose exec -T db pg_restore \
  --username "$db_user" \
  --dbname "$scratch_db" \
  --exit-on-error \
  --no-owner \
  --no-privileges < "$backup_path"

migration_count=$(docker compose exec -T db psql \
  --username "$db_user" \
  --dbname "$scratch_db" \
  --tuples-only \
  --no-align \
  --command "SELECT COUNT(*) FROM django_migrations;")

if [ "$migration_count" -lt 1 ]; then
  echo "Restore check failed: no migration records found." >&2
  exit 1
fi

echo "Restore rehearsal passed with $migration_count migration records."
