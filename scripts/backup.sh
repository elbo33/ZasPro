#!/usr/bin/env bash
# Dump the local Postgres database to backups/ with a dated filename.
#
#   ./scripts/backup.sh
#
# The database is the *working* store; git holds the record of truth (ADR 0011:
# committed knowledge/ files, the source documents, the migration chain). This
# dump is a convenience for fast local recovery — it is NOT the source of truth
# and backups/ is gitignored.
#
# WARNING: `docker compose down -v` deletes the Postgres volume. Run this first,
# or be ready to rebuild from git + sources (uv run alembic upgrade head; seed;
# re-ingest; re-map; re-import knowledge/).
set -euo pipefail
cd "$(dirname "$0")/.."

PGUSER="${PGUSER:-zaspro}"
PGDATABASE="${PGDATABASE:-zaspro}"
mkdir -p backups
stamp="$(date +%Y%m%d-%H%M%S)"
out="backups/zaspro-${stamp}.sql.gz"

if command -v pg_dump >/dev/null 2>&1 && [ -n "${USE_LOCAL_PGDUMP:-}" ]; then
  pg_dump -h localhost -U "$PGUSER" "$PGDATABASE" | gzip > "$out"
else
  docker compose exec -T db pg_dump -U "$PGUSER" "$PGDATABASE" | gzip > "$out"
fi

echo "wrote $out ($(du -h "$out" | cut -f1))"
ls -1t backups/*.sql.gz | tail -n +11 | xargs -r echo "old backups you may want to prune:"
