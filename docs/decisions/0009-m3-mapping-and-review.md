# ADR 0009 — M3 mapping agent and review queue

Status: accepted
Date: 2026-08-27

## Context

M3 (SPEC §17) needs a mapping agent that records confidence, a review-queue
backend, a keyboard-driven review UI, and a dashboard skeleton with curriculum
and source pages. Gate: *"I can approve and reject mappings by keyboard without
touching the mouse, and deterministically extracted chunks do not clutter the
queue."*

Relevant constraints: SPEC §9 (one typed queue, risk-sorted, deterministic
content stays out by default, keyboard approve/reject/edit, one item per screen,
batch approval, every decision records reviewer + timestamp + prior status,
rejection needs a reason code), §10 (`confidence` + `mapping_status`, mapping
confidence separate from extraction confidence, unmapped is a normal state
visible as a count), §12 (`LLM → structured response → Pydantic → business-rule
validation → database`, never `LLM → database`; constraints in validators not
prompts), §16 (FastAPI internal API; Next.js App Router dashboard, read-mostly,
never touches Postgres).

## Decisions

### 1. Mapping confidence drives queue entry; one threshold

`chunk_mappings.confidence` is the **mapping agent's** confidence, stored
separately from `source_chunks.confidence` (extraction; NULL = deterministic).
`AUTO_APPROVE_THRESHOLD = 0.80` (`zaspro.mapping.agent`): at or above it the
mapping is `AI_SUGGESTED` and no review item is created; below it the mapping is
`REVIEW_REQUIRED` and gets exactly one `ReviewItem`.

This is the whole mechanism behind "deterministically extracted chunks do not
clutter the queue": clean pandoc text is easy to map, so it maps confidently, so
it never reaches the queue. Deterministic *extraction* is not by itself a reason
to review — only an uncertain *mapping* is (SPEC §9). An unreviewed low-
confidence guess is **not** written onto `exercises.topic_id`; only an
`AI_SUGGESTED` (confident) or human-`APPROVED` mapping propagates.

**0.80 is now evidence-based, but thinly.** Calibration pass on 27 Aug 2026:
`MMAP-P0-660-A-2405-arkusz.docx` mapped with `ClaudeMappingAgent`
(`claude-opus-5`), threshold 1.01 so all 37 chunks queued, reviewed by keyboard.
Result (`m3/mapping_calibration.md`):

| band | n | accepted unchanged | agreement |
|---|---|---|---|
| [0.0, 0.5) | 1 | 0 | 0% |
| [0.5, 0.7) | 9 | 9 | 100% |
| [0.7, 0.8) | 4 | 3 | 75% |
| [0.8, 0.9) | 9 | 9 | 100% |
| [0.9, 1.0] | 14 | 14 | 100% |

35/37 accepted unchanged; both corrections fell below 0.8; everything at or
above 0.8 was accepted. `AUTO_APPROVE_THRESHOLD = 0.80` is set from this. It is
still a parameter of `map_chunk` / `map_document` / `MAP_CHUNK`, not a baked
constant.

**Caveats, on the record:** one paper, 37 samples, a single reviewer. The
[0.7, 0.8) band (n=4, 75%) and [0.0, 0.5) band (n=1, 0%) are too thin to draw a
line through — 0.80 is the boundary *below* which the two errors happened, not a
statistically defended cutoff. **Revisit once a few hundred mappings have been
reviewed** (the audit sampler feeds this continuously), and re-run
`zaspro.review.calibration_run`.

**Recommender bug fixed in the same pass.** The first cut of
`agreement_curve` skipped bands with n<5 when picking a recommendation, so it
ignored the n=1 band at 0% and the n=4 band at 75% and returned `0.00` — which,
taken literally, auto-approves the mapping that was rejected outright. Now a
band below the target blocks the cutoff regardless of sample count, and when the
band that would sit at the cutoff is thin the tool reports "insufficient data",
never a number. `--review-all` forces every mapping into the queue for future
calibration passes; `--remap` re-runs an already-mapped paper.

### 2. `StubMappingAgent` for the offline path

`zaspro.mapping.agent` ships two implementations behind one Protocol:

* `ClaudeMappingAgent` — `claude-opus-5`, adaptive thinking, one structured
  tool (`record_mapping`), Pydantic on the way out. Used when
  `ANTHROPIC_API_KEY` is set.
* `StubMappingAgent` — deterministic, no network. Reads any requirement code the
  chunk already cites (`I.4)` style) and falls back to token overlap with the
  candidate requirement prose. Not a model — a cheap signal so the entire M3
  path (jobs, queue, API, dashboard) is runnable and testable without a key.

`default_agent()` picks between them by key presence. Consequence: with the
stub, real arkusz exercise statements (which cite no codes) all land in review —
consistent with SPEC §9's "expect a substantial fraction of the corpus in human
review". The real agent's confidence is what the threshold acts on in
production.

### 3. Candidate set is podstawowy leaf requirements only

Per ADR 0008, `candidate_topics()` offers only `level = podstawowy` topics with
an `official_requirement_code`. A mapping to any other topic (e.g. a deferred
rozszerzony requirement) fails business-rule validation and the job retries.

### 4. Business rules live in `handler.py`, not the prompt

`map_chunk()` enforces: chosen `topic_id` ∈ the candidate set (or `NULL`);
`confidence ∈ [0,1]`; `content_type` a valid enum; `difficulty ∈ 1..5` or
`NULL`. A violation raises `MappingError`; the worker records it and retries.
Feeding the validation text back into a retry prompt (SPEC §12) is left for when
`ClaudeMappingAgent` is exercised at corpus scale — noted, not built.

### 5. Review queue is a thin service over three tables

`chunk_mappings`, `review_items`, `review_decisions` (migration
`0004_mapping_and_review`). `zaspro.review.queue`:

* `next_item()` — highest `risk` (`1 - confidence`) OPEN item; `exclude_ids`
  lets the UI page forward ("skip") without resolving anything.
* `record_decision()` — appends an immutable `ReviewDecision` (reviewer,
  decision, prior status, reason code, note), updates `ReviewItem.status` /
  `resolved_at`, and propagates to the `ChunkMapping` and the exercise row.
  REJECT without a `reason_code` raises (the DB `CHECK` enforces it too). EDIT
  applies field changes and leaves the item OPEN for a follow-up approve.
* `batch_approve()` — approves several items that share one `(topic_id,
  source_document_id)` and are all above `BATCH_MIN_CONFIDENCE = 0.6`; otherwise
  nothing is written (SPEC §9 "sharing high confidence and the same topic and
  source").

### 6. FastAPI + Next.js as the SPEC names them

`fastapi` + `uvicorn` (Python) and a Next.js 14 App Router app in `dashboard/`
(Node). Both bring infrastructure, but SPEC §3 and §16 name them explicitly, so
this is executing a settled decision, not making a new one. `httpx` is added
dev-only for `fastapi.testclient`. The dashboard talks only to the API; it never
imports `zaspro` or touches Postgres. The review page is one client component
with a `window` keydown handler: `a` approve, `r` then `1–6` reject-with-reason,
`e` then `j`/`k`/`Enter` edit topic, `s` skip, `b` batch-approve the current
group. No route changes between items — decisions return the next item and fresh
stats in the response body.

### 7. Threshold calibration instrumentation (migration 0005)

So the threshold is set from data, not a feeling:

* **`review_decisions.mapping_confidence`** — the `ChunkMapping`'s confidence is
  frozen onto every decision at the moment it is made, so the
  agreement-vs-confidence curve is real recorded data, not a later join that
  could drift if a mapping is re-run.
* **`zaspro.review.calibration.agreement_curve`** buckets resolved
  CURRICULUM_MAPPING reviews into confidence bands `[0,.5) [.5,.7) [.7,.8)
  [.8,.9) [.9,1]` and reports, per band, how often the reviewer accepted the
  mapping unchanged (APPROVE, no prior EDIT) vs changed/rejected it. It
  recommends the lowest band boundary at/above which every band clears 95%
  agreement with ≥5 samples. Exposed at `GET /review/calibration`, written to
  `m3/mapping_calibration.md` by `zaspro.review.calibration_run`, shown on the
  dashboard `/calibration` page.

* **`zaspro.mapping.run` fails loudly, and re-maps on demand.** A calibration
  command that silently no-ops is how you calibrate against the wrong data, so:
  cheap local checks first (doc exists, has chunks, has something to do) each
  exit `2` with the reason; then, when the agent is Claude, a one-token
  `preflight()` call proves the key/model/network before 37 jobs are enqueued
  and prints the model the API echoed back. `--remap` re-runs chunks that
  already have a mapping (drops the old `ChunkMapping` and its review item
  first) — the path from a stub run to a real Claude run for the calibration
  pass. `ClaudeMappingAgent` now takes its key from `zaspro.config`
  (pydantic-settings reads `.env`; the SDK alone only reads `os.environ`).
* **`review_items.audit_sample`** + **`DEFAULT_AUDIT_SAMPLE_RATE = 0.03`** — a
  permanent random fraction of *confident* (`AI_SUGGESTED`) mappings is queued
  anyway, flagged `audit_sample`, at low `risk`, without blocking the mapping
  (topic still propagates). The pick is deterministic per `(chunk_id, prompt
  version)` so a re-run is stable and a new prompt re-rolls. This means **no
  threshold setting can put the system in a state where a large block is
  auto-approved with no human ever seeing a sample of it** — the rate is not
  reachable-to-zero without a code change. Tune it after the calibration pass;
  if the real agent turns out confident on ~everything, the rate is the lever,
  not the threshold.

## What this does not touch

No knowledge extraction, no dedupe/merge, no normalisation, no exercise
generation (M4/M5). `EXTRACTION_CONFLICT` / `NORMALISATION_FAILURE` /
`MERGE_CANDIDATE` review-item types exist in the enum but nothing produces them
yet.
