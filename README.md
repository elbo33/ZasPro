# ZasPro

Polish Matura knowledge base and episode planning system. The authoritative
spec is [`docs/SPEC.md`](docs/SPEC.md); architectural decisions are ADRs in
[`docs/decisions/`](docs/decisions/).

Build state: **M2 (ingestion)** — Track A pipeline behind a job system.

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

## Tests

```sh
uv run pytest
```

DB-backed tests use a `zaspro_test` database and skip if PostgreSQL is not
reachable. `test_seed_latex.py` skips without a TeX install.
