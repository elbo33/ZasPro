# ADR 0007 — M2 job system and ingestion shape

Status: accepted (M2)
Date: 2026-08-27

## Context

M2 productionises the M0.2 Track A wrapper behind a job system and lands its
output in the schema. Decisions that shape everything built on top.

## Decisions

### 1. The queue is a Postgres table

`jobs` + a single-process `Worker`. Claiming is
`SELECT … WHERE status='pending' ORDER BY id FOR UPDATE SKIP LOCKED LIMIT 1`, so
several workers can run without a broker. No Celery / Redis / RabbitMQ until the
simple version is provably insufficient (SPEC §3). `run_forever()` polls;
`drain()` runs to empty for scripts and tests.

One job per transaction. On a handler exception the row goes back to `pending`
while `attempts < max_attempts`, then `failed`, with the traceback in `error`.
Retries are per-row (SPEC §15) — a failed figure does not re-run the document.

### 2. Ingestion splits into a deterministic core and a figure job

`INGEST_DOCUMENT` runs the deterministic pipeline synchronously (pandoc
convert → strip boilerplate → `Zadanie` segmentation → `<w:drawing>` count →
**marking-scheme cross-validation as a hard gate**, `GateFailed` fails the job)
and persists `source_document`, `source_chunks` and `exercises`. It then
enqueues one `RENDER_VECTOR_FIGURE` per figure-bearing task.

Figure rendering is a separate job because LibreOffice is slow and fails
independently. `pipeline.py` is split into `segment_document` +
`validate_against_marking` so tests exercise the halves with synthetic input;
`run_pipeline` composes them with `parse_marking_scheme` for the handler.

### 3. Figure loss is structural, not silent (the M0.4 finding)

`exercises.expected_figure_count` is populated during segmentation from the
per-task `<w:drawing>` count. A subtask inherits its parent's count (the figure
sits in the parent's range). `RENDER_VECTOR_FIGURE` links the one `Figure` to
the task **and its subtasks** (SPEC §5: a figure can serve several subtasks).
`build_report` lists any exercise where `expected_figure_count` exceeds its
count of linked `render_status = COMPLETE` figures; the M2 gate requires that
list to be empty. A render that never succeeds leaves the exercise visibly
incomplete — it is never an empty success.

### 4. `source_chunks.confidence` is nullable, no default

Confirmed with the reviewer. NULL = deterministic; M3 review triage keeps those
chunks out of the queue. The persist layer sets it explicitly to `None` for
every pandoc chunk. A `NOT NULL` or a default would undo the M0 finding.

### 5. `exercises` at extraction time only

M2 fills number, points, parent link, raw LaTeX, `origin = OFFICIAL`,
`verbatim_ok` (from the source), `variant_group_id`
(`{session}-{level}-{number}`, so an A/B pair joins without ever merging — SPEC
§8), and `expected_figure_count`. `topic_id` is NULL until M3 mapping;
`statement_latex_normalised`, `solution*`, `final_answer_repr` and
`verification_status` beyond `DRAFT` are M5. The stem is not denormalised —
`Exercise.full_statement` walks `parent_exercise_id` at read time (SPEC §5).

### 6. Storage behind an interface

`zaspro.storage.Storage` protocol with `LocalStorage`. Figure PNGs and the
rendered PDF go through it (`STORAGE_ROOT`). An S3 implementation is a new class
behind the same protocol; deferred until something needs it (SPEC §3 — "the
smallest thing"). No object storage for video/audio (SPEC scope).

## No new dependencies

M2 adds none. pandoc / poppler / LibreOffice are subprocesses (already in
`dependencies.md`); SQLAlchemy / psycopg / PyYAML came with M1.
