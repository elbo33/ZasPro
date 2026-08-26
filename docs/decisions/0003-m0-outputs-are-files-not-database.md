# ADR 0003 — M0 emits files, not database rows

Status: accepted (M0.2)
Date: 2026-08-26

## Context

SPEC M0.2 says the wrapper "writes chunks with `extraction_method =
'pandoc_omml'` and `confidence = NULL`". Those are `source_chunks` column
names from the §5 data model, which could be read as "M0 writes to Postgres".

But M1 is explicitly "Docker Compose with Postgres, Alembic wired … curriculum
tables", and SPEC §5 says "create tables in migration batches per phase". There
is no schema, no migration system, and no database in M0.

## Decision

M0 serialises its output as **Pydantic models → JSONL / Markdown on disk**:

- `m0/segmentation/<doc>.jsonl` — one `ExerciseChunk` per line
- `m0/corpus_split.md`, `m0/segmentation_gate.md`, later `m0/*.md` reports
- `m0/_work/` — pandoc intermediates (`.tex`, extracted media), gitignored
- committed: the reports, JSONL, and the M0.6 curriculum seed

The `ExerciseChunk` model carries `extraction_method` and `confidence` fields
now, so the shape is stable when M2 productionises this into the DB.

## Consequences

- No SQLAlchemy / Alembic dependency in M0.
- M2 ("Track A pipeline productionised from the M0 wrapper") maps these models
  onto `source_chunks` / `exercises` rows; field names already line up.
- The M0.2 gate is a script exit code + a Markdown report, not a DB constraint.
