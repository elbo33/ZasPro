#!/usr/bin/env bash
# Restore the local Postgres database from a backups/ dump.
#
#   ./scripts/restore.sh backups/zaspro-20260828-120000.sql.gz
#
# This DROPs and recreates the public schema before loading — every current row
# is replaced by the dump's. Stop the API / workers first.
set -euo pipefail
cd "$(dirname "$0")/.."

file="${1:-}"
if [ -z "$file" ] || [ ! -f "$file" ]; then
  echo "usage: $0 <backups/zaspro-YYYYMMDD-HHMMSS.sql.gz>" >&2
  echo "available:" >&2
  ls -1t backups/*.sql.gz 2>/dev/null >&2 || echo "  (none)" >&2
  exit 2
fi

PGUSER="${PGUSER:-zaspro}"
PGDATABASE="${PGDATABASE:-zaspro}"

read -r -p "Replace ALL data in '$PGDATABASE' with '$file'? [y/N] " ans
[ "$ans" = "y" ] || [ "$ans" = "Y" ] || { echo "aborted."; exit 1; }

docker compose exec -T db psql -U "$PGUSER" -d "$PGDATABASE" -v ON_ERROR_STOP=1 \
  -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
gunzip -c "$file" | docker compose exec -T db psql -U "$PGUSER" -d "$PGDATABASE" -v ON_ERROR_STOP=1

echo "restored $PGDATABASE from $file"
