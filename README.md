# ZasPro

Polish Matura knowledge base and episode planning system. The authoritative
spec is [`docs/SPEC.md`](docs/SPEC.md); architectural decisions are ADRs in
[`docs/decisions/`](docs/decisions/).

Build state: **M1 (foundation)** — schema, migrations, seeding.

## Setup

```sh
uv sync                       # Python 3.12 env + deps (managed by uv)
cp .env.example .env          # DATABASE_URL, ANTHROPIC_API_KEY, STORAGE_ROOT
docker compose up -d db       # PostgreSQL 16
uv run alembic upgrade head   # apply migrations
uv run python -m zaspro.seeding.run   # seed curriculum + sources (idempotent)
```

## Layout

```
src/zaspro/
  config.py            env / .env settings
  db/                  SQLAlchemy 2.x models, engine, session
  seeding/             idempotent curriculum + source seeding
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
