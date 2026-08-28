# ZasPro

Polish Matura knowledge base and episode planning system. The authoritative
spec is [`docs/SPEC.md`](docs/SPEC.md); architectural decisions are ADRs in
[`docs/decisions/`](docs/decisions/).

Build state: **M4 (knowledge layer)** — a teaching tree of 50 sections; the
agent writes each section's knowledge as a textbook would; review and export to
committed files.

## Setup

```sh
uv sync                       # Python 3.12 env + deps (managed by uv)
cp .env.example .env          # DATABASE_URL, ANTHROPIC_API_KEY, STORAGE_ROOT
docker compose up -d db       # PostgreSQL 16
uv run alembic upgrade head   # apply migrations
uv run python -m zaspro.seeding.run   # seed curriculum + sources (idempotent)

# ingest one arkusz end to end (needs pandoc, LibreOffice, poppler)
uv run python -m zaspro.ingestion.run \
  MMAP-P0-660-A-2605-arkusz.docx MMAP-P0-100-2605-zasady.pdf
```

## Layout

```
src/zaspro/
  config.py            env / .env settings
  storage.py           storage interface (LocalStorage; S3 later)
  db/                  SQLAlchemy 2.x models, engine, session
  seeding/             idempotent curriculum + source seeding
  jobs/                Postgres-backed queue + worker loop
  ingestion/           Track A pipeline + job handlers (M2)
  extraction/          Track A DOCX -> LaTeX -> segmented chunks (M0)
  m0/                  M0 milestone runners (reports under m0/)
alembic/               one linear migration chain
seeds/                 hand-verified curriculum seed + review sheets (M0.6)
sources/               MANIFEST.md (authoritative) + raw/ (read-only, gitignored)
docs/                  SPEC.md, sources.md, decisions/
```

## Knowledge layer (M4)

The teaching tree is seeded from `seeds/teaching_sections.yaml` by
`zaspro.seeding.run`. The agent then writes each section's spec:

```sh
uv run python -m zaspro.knowledge.write ciag-arytmetyczny funkcja-liniowa
uv run python -m zaspro.knowledge.write --all      # every section (asks first)
```

Each run leaves one `KNOWLEDGE_SPEC` review card per section. Review in the
dashboard (Knowledge tab), then freeze the approved ones to git:

```sh
uv run python -m zaspro.knowledge.export --all     # writes knowledge/sections/<slug>.yaml
```

The committed YAML is the record of truth (ADR 0012). `knowledge.write` refuses
to re-run a section that has one unless `--force`.

## Backups

The database is the **working** store; git holds the record (committed
`knowledge/` files, `sources/` documents, the migration chain). Everything in
Postgres should be rebuildable from those. A local dump is still a convenience:

```sh
./scripts/backup.sh                                  # -> backups/zaspro-<date>.sql.gz
./scripts/restore.sh backups/zaspro-<date>.sql.gz    # replaces all current data
```

`backups/` is gitignored. **`docker compose down -v` destroys the Postgres
volume** — run `backup.sh` first, or be prepared to rebuild from git + sources.

## Tests

```sh
uv run pytest
```

DB-backed tests use a `zaspro_test` database and skip if PostgreSQL is not
reachable. `test_seed_latex.py` skips without a TeX install.
