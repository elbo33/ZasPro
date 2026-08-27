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

Two figure quantities that are **not** the same, split across two columns so a
report can never make them look contradictory (migration `0003`):

* `exercises.own_figure_count` — `<w:drawing>` count in the exercise's *own*
  DOCX range. `> 0` marks a distinct **figure region**; each yields one
  `Figure` row.
* `exercises.expected_figure_count` — own + inherited. A subtask inherits its
  parent's count (the figure sits in the parent's range), so it needs a figure
  attached without being its own region.

`RENDER_VECTOR_FIGURE` links the one `Figure` to the region task **and its
subtasks** (SPEC §5). `build_report` reports `figure_regions_expected`
(`own_figure_count > 0`) vs `figure_regions_rendered` (`Figure` rows,
`COMPLETE`) as one comparable pair, `figure_bearing_exercises`
(`expected_figure_count > 0`) as a separate count, and `incomplete` as the list
of exercises where `expected_figure_count` exceeds linked-and-`COMPLETE`
figures. The gate requires `regions rendered == regions expected` **and**
`incomplete == []`. For the reference arkusz: 8 regions, 8 rendered, 12
figure-bearing exercises (8 + 4 inheriting), 0 incomplete.

A render that never succeeds leaves its exercise in `incomplete` with a
`FAILED` job carrying the traceback — never an empty success. Exercised end to
end by `test_ingestion_incomplete_e2e.py` (a synthetic arkusz with an empty
`<w:drawing>` that LibreOffice renders as no ink, so the crop genuinely fails).

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

### 7. Batch ingestion of the Track A corpus

`zaspro.ingestion.batch` discovers Track A from `sources` (EXAM rows with a
`.docx` file), resolves each one's marking scheme, ingests it via the job
system one document at a time (`enqueue` + `Worker().drain()`), and writes
`m2/corpus_track_a_summary.md`.

`resolve_marking_scheme` handles the naming variation: it drops the `-A`/`-B`
version letter and tries `MMAP-{lvl}-660-{session}-zasady.pdf` (czarnodruk,
maj-2025 only) then `MMAP-{lvl}-100-{session}-zasady.pdf`. Upstream the file
sits under different directories per year; all files are flat in
`sources/raw/`, so that is not our problem.

**Corpus result (maj-2024, -2025, -2026 podstawowy):** 3/3 pass the gate with
**no change** to `strip_boilerplate` or `segment_arkusz` — the three sessions
are structurally identical. Point totals 46 / 50 / 50, each independently
confirmed by the arkusz's own cover text. 22 figure regions across the three,
every one a Word-drawn shape, all rendered. Loose figure crops (M0.4 mode 4,
ADR 0004) recur but do not affect the gate; tightening is M6-adjacent quality
work.

**Informatory** are not run through the pipeline — they are prose + worked
examples, no marking scheme, no `Zadanie`-list structure. The batch does a
structural audit only (oMath / drawings / marker counts). Semantic chunking of
them needs `content_type` classification, which is review-queue / Ingestion
Agent work (M3+), scoped separately. They are reported explicitly, never as a
silent Track A failure.

**Track B** (rozszerzony everything, version B papers — PDF only, no
czarnodruk in any Formuła 2023 session) is given a bare `source_documents` row
with `extraction_status = pending` and left uningested (ADR 0005). This
matters for M3: roughly half the seeded curriculum (all `rozszerzony` topics)
currently has no deterministic source.

### 7a. Extending Track A to seven sessions (2203, 2209, 2305, 2312)

The manifest gained four pre-Formuła-2023 podstawowy czarnodruk papers. What
the parser (not the documents) needed:

* **DOCX naming.** Two conventions: `MMAP-P0-660-A-2405-arkusz.docx` and the
  older `MMAP-P0-660-2305.docx` (no version letter, no `-arkusz`). `_ARKUSZ`
  and `persist._MMAP` accept both; a missing letter leaves `paper_version`
  **NULL**, never defaulted to `A`.
* **Marking-scheme discovery.** Older sessions ship one zasady PDF whose name
  concatenates every paper code
  (`MMAP-P0-100-200-300-400-660-700-Q00-2209-zasady.pdf`).
  `resolve_marking_scheme` now globs `MMAP-{lvl}-*-{session}-zasady.pdf` and
  prefers a name carrying the `660` token — that token is the reliable "a
  czarnodruk exists for this session" signal (MANIFEST note, better than link
  scraping); `corpus.py` uses it too.
* **Marking-scheme subtask notation.** Those PDFs write subtasks `Zadanie 13.1
  (0–1)` — no period after the number — vs the 2024+ `Zadanie 13.1. (0–1)`.
  `marking_scheme._TASK_LINE` now treats the period as optional. This reads the
  oracle correctly; the gate (exact arkusz ↔ marking-scheme agreement) is
  unchanged.
* `strip_boilerplate` / `segment_arkusz`: **still zero changes.** The predicted
  segmentation drift did not appear in any of the seven.
* **Re-ingest idempotency.** `persist_ingestion` now deletes a document's
  `figures` before its `exercises` on re-ingest; without that the
  `exercise_figures` association delete raised `StaleDataError`. The batch is
  now idempotent (verified: 7/7 on a second run against the same DB).

**Result: 7/7 pass**, after two parser fixes above plus two hand-authored
source-defect files (never inference):

* **`sources/marking_scheme_overrides.yaml`** — 2209's zasady PDF omits the
  `(0–1)` range on the heading `Zadanie 10.3.` that every sibling carries; the
  "Zasady oceniania" block below it and the arkusz's 46-pt cover both confirm
  0–1. A human recorded that one value with the page reference. `_TASK_LINE`
  never infers a missing range — that would defeat the check the gate performs.
* **`sources/figure_overrides.yaml`** — re-checking every task drawing across
  all seven papers (reusing the real marker walker) confirmed **every genuine
  exercise figure is a `WORD_SHAPE`** in all seven; the earlier claim that the
  older papers carried task *raster* figures was a measurement error (a
  throwaway scan with a broken marker regex misattributed chrome images to
  tasks). What the older papers do carry is the occasional orphaned drawing
  group: **2209 Zadanie 10.1, 2312 Zadanie 11.4, 2605 Zadanie 32** each have a
  `<w:drawing>` with no text box, no image, only bare connector/line/rectangle
  shapes, on a "Dokończ zdanie" / multiple-choice question that uses the
  parent's figure or needs none. Each is recorded by hand with
  `expected_figure_count: 0`. `count_drawings_by_task` applies the file last;
  the `RASTER`/`WMF` handlers stay wired to `source_format` for a future source.

The **2412** próbny (Dec 2024, under the `_OD_2015` path) was checked from its
cover: it reads "Formuła 2023", podstawowy, 50 pts — **not** a Formuła 2015
exclusion. It has no czarnodruk DOCX, so it is PDF-only Track B (recorded as
such in the manifest), not one of the seven.

## No new dependencies

M2 adds none. pandoc / poppler / LibreOffice are subprocesses (already in
`dependencies.md`); SQLAlchemy / psycopg / PyYAML came with M1. The
`sources/*_overrides.yaml` files are read with PyYAML.
