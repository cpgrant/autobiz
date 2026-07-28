#!/bin/sh
set -eu

backup_dir=${1:-backups/local}
db_name=${DB_NAME:-autobiz}
db_user=${DB_USER:-autobiz}
timestamp=$(date -u +%Y%m%dT%H%M%SZ)
backup_path="$backup_dir/autobiz-$timestamp.dump"

mkdir -p "$backup_dir"

docker compose exec -T db pg_dump \
  --username "$db_user" \
  --dbname "$db_name" \
  --format custom \
  --no-owner \
  --no-privileges > "$backup_path"

if [ ! -s "$backup_path" ]; then
  echo "Backup file is empty: $backup_path" >&2
  exit 1
fi

echo "$backup_path"
