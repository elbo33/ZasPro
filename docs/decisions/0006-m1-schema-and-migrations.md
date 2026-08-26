# ADR 0006 — M1 schema and migration choices

Status: accepted (M1)
Date: 2026-08-27

## Context

M1 creates the first migration batch: curriculum (`subjects`, `units`,
`topics`, `topic_prerequisites`) and `sources`. Several small decisions were
made that are easier to change now than later.

## Decisions

### 1. One migration per batch, meaningful id, file named by id

`0001_curriculum_and_sources`. `alembic.ini` sets `file_template = %(rev)s`, so
the file is `alembic/versions/0001_curriculum_and_sources.py` — no hash, no
duplicated slug (SPEC §15). `env.py` takes the DB URL from `zaspro.config`, not
`alembic.ini`.

### 2. Enums as `VARCHAR + CHECK`, not native PG enums

Every enum column uses `sa.Enum(..., native_enum=False)`. Native PG enums need a
migration and a table rewrite to add a value; a `CHECK` constraint is a one-line
`ALTER`. The schema will gain enum values often (new `source_type`s, statuses).

### 3. `units.code`, and the `R` marker in `topics.official_requirement_code`

SPEC §5 lists `official_requirement_code` on `topics` only. `units` also gets a
`code` (the Roman numeral `I`..`XIII`) as its natural key for idempotent
seeding and as the link to the regulation's section numbering.

`rozszerzony` requirements restart numbering at `1)` in the regulation, so their
codes would collide with `podstawowy` (`I.1` twice). The seed disambiguates with
an `R`: `I.1` (podstawowy) vs `I.R1` (rozszerzony). `official_requirement_code`
stays globally unique, and `level` still tells them apart. This is a synthetic
convention, documented in `m0/curriculum_notes.md`.

### 4. Acyclicity by trigger, using the `CYCLE` clause

`topic_prerequisites` is a DAG. A `BEFORE INSERT OR UPDATE` trigger
(`topic_prerequisites_reject_cycle`) walks prerequisite edges from the new
edge's target and raises `check_violation` if it can reach the new edge's
source. It uses PostgreSQL's `CYCLE id SET is_cycle USING cycle_path` (PG 14+)
so the check itself cannot loop on already-cyclic data (SPEC §5: "at write
time … rather than trusting the seeding process"). A separate `CHECK` rejects
self-edges. `topic_prerequisites` is empty after M1 seeding — the podstawa does
not encode prerequisites; they are added later by hand or model inference,
which is exactly why the guard is in the database.

### 5. `sources` only; `source_documents` is M2

Each `sources/MANIFEST.md` row becomes one `sources` row keyed by `file_ref`.
Document-level fields (`variant`, `session`, `paper_version`) are carried in
`notes` and get real `source_documents` rows in M2. Licensing enums
(`source_type`, `licence_status`) mirror the manifest's vocabulary exactly, so
an unknown value fails at seed time rather than being coerced (SPEC M1: "Do not
have a model generate or infer licensing metadata").

### 6. Idempotent seeding via natural-key upsert

`zaspro.seeding.upsert.upsert()` looks a row up by its natural key
(`subjects.slug`, `(units.subject_id, units.code)`,
`topics.official_requirement_code`, `sources.file_ref`), syncs mutable fields,
and reports `created` / `updated` / `unchanged`. Re-running `zaspro.seeding.run`
is a no-op; editing a row and re-running repairs it.

## Alternatives rejected

- **`ltree` / materialized path for the curriculum tree** — the tree is ~130
  nodes, shallow, read-only after seeding. Adjacency list is enough and keeps
  reparenting a single-row update (SPEC §5).
- **Application-level cycle check in the seeder** — SPEC §5 explicitly wants the
  guard in the database, not the seeding process.
- **Native PG enums** — see decision 2.
