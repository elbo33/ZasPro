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

**0.80 is validated, twice.** Two calibration passes on
`MMAP-P0-660-A-2405-arkusz.docx` (`ClaudeMappingAgent`, `claude-opus-5`,
threshold 1.01 so every chunk queued, ~37 mappings reviewed by keyboard each):
v1 under the single-topic contract, v2 under multi-topic (migration 0006). Both
agree — **every reviewer correction fell below 0.8; everything at or above 0.8
was accepted unchanged.** `AUTO_APPROVE_THRESHOLD = 0.80` is set from this and
kept as a parameter of `map_chunk` / `map_document` / `MAP_CHUNK`.

v1 bands: `[0,.5) 1@0% · [.5,.7) 9@100% · [.7,.8) 4@75% · [.8,.9) 9@100% ·
[.9,1] 14@100%` (`m3/mapping_calibration_v1_singletopic.md`).

**The contract change worked — this is the evidence, not just tidiness.** From
v1 to v2 the confidence distribution moved as predicted: **above 0.9 went 14 →
20; the mid-range [0.5, 0.8) went 13 → 7.** Once the agent could record "also
tests X" as a secondary instead of hedging its primary, it stopped spreading
uncertainty across the scale for tasks it actually understood. v2 curve at
`m3/mapping_calibration.md`.

**Caveats still on the record:** one paper, ~37 samples, one reviewer per run;
the bands below 0.8 remain thin. The 3% audit sampler keeps feeding the curve —
revisit after a few hundred reviewed mappings.

### 1a. The stem defect and its effect on the curve (28 Aug 2026)

Working the 104-decision queue (the v2 pass + the six-paper run) surfaced a
pipeline bug: **`map_chunk` passed only the subtask's own body to the agent,
not the parent's shared stem.** The stem was in the DB (parent chunk row;
`Exercise.full_statement`), but the mapping pipeline reads `source_chunks` and
built `MappingRequest` from `chunk.text` alone. A subtask read without its stem
("the 50th term of the sequence is …") is usually unmappable, so those were
rejected — recording the agent as wrong on broken input.

Fixed (`PROMPT_VERSION` → `m3-map-v2`): `MappingRequest` gains `stem` /
`stem_latex`, `_parent_chunk` supplies them for `Zadanie N.M` fragments, the
system prompt and the review card show the stem. `review_items.input_defect`
(migration 0007) marks decisions made on the broken input;
`flag_stem_defect_reviews` set it on the **32** resolved subtask decisions;
`agreement_curve` excludes them.

**Effect on the sub-0.8 bands:** removing the 32 lifts [0.5,0.7) 66% → 83% and
[0.0,0.5) 14% → 33%. It does **not** move the recommendation — the six-paper
run had already put enough clean samples in [0.7,0.8) that the contaminated
104-decision curve also recommended 0.70.

### 1b. AUTO_APPROVE_THRESHOLD = 0.70 (28 Aug 2026)

After `--remap-defective` (the 32 flagged subtasks re-mapped with their stems)
and re-review, the curve is:

| band | n | agreement |
|---|---|---|
| [0.0, 0.5) | 3 | 33% |
| [0.5, 0.7) | 23 | 83% |
| **[0.7, 0.8)** | **25** | **100%** |
| [0.8, 0.9) | 8 | 100% |
| [0.9, 1.0] | 23 | 100% |

**Set `AUTO_APPROVE_THRESHOLD = 0.70`.** Curve provenance: seven papers,
top-level *and* subtask, multi-topic contract, prompt `m3-map-v2`, stem defect
cleared. 56 decisions at or above 0.70, every one accepted unchanged. The
[0.7,0.8) band went from n=4 (75%, the point that pinned v1 at 0.80) to n=25
(100%) — **the drop from 0.80 to 0.70 is from more data in that band, not from
the defect fix.** Bands below 0.70 still carry real disagreement (83% / 33%),
so 0.70 is the floor, not a suggestion to go lower.

**Count reconciliation** (why the curve shows 82, not 104): the 72 top-level
decisions are untouched. Of the 32 flagged subtask items, `--remap-defective`
deleted the items and decisions, then re-mapped with the stem — **22 now map at
≥ 0.70 and are `AI_SUGGESTED` (no review item, no decision needed)**; the other
**10** stayed sub-threshold, were re-reviewed, and all 10 were APPROVED (zero
subtask rejections after the fix — the 11 earlier were all broken-input). 72 +
10 = 82. The 22 are not lost: the mappings exist, feed coverage and M4; there
is simply no longer a human decision to make on them. Separately, 22 *other*
subtask primaries had mapped confidently on the stem-less body at v1 and never
entered the queue; `--remap-defective` now also sweeps those (any subtask
primary with `prompt_version != PROMPT_VERSION`), so M4 does not aggregate from
stem-less subtask mappings.

**Recommender bug fixed during the v1 pass.** The first cut of
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

### 8. Multi-topic mapping (migration 0006)

The scan in `m3/mapping_multitopic_scan.md` settled it: 17 of 37 real mappings
name a second requirement the fragment also tests, and **every** mapping the
agent scored below 0.8 does. The single-topic contract was forcing a "which is
*the* one?" choice the exam doesn't make. Doing this before M4 rather than after
because M4 knowledge specs would bake in the single-topic assumption.

* **Schema.** `chunk_mappings` drops `uq_chunk_mappings_chunk` and gains
  `is_primary`; a partial unique index (`uq_chunk_mappings_primary … WHERE
  is_primary`) keeps exactly one primary per chunk, secondaries unlimited.
* **Agent.** `MappingResult.secondary_topics: list[{topic_id, confidence,
  rationale}]`. The prompt asks for "the primary requirement plus any others
  the fragment genuinely also tests"; confidence stays "am I right", not "is
  this primary". `map_chunk` validates each secondary against the candidate set,
  drops any equal to the primary or duplicated, and writes 1 + N rows (all same
  provenance). A chunk's review item still targets the primary row.
* **Review.** `ReviewDecisionType.PROMOTE` + `_promote_secondary`: swap a
  secondary into the primary slot (two `UPDATE`s with a flush between — the
  partial index forbids two primaries even transiently), re-point the review
  item, resolve as APPROVED. One keystroke (`p`; `p` then a digit when there
  are several). The demoted row stays `AI_SUGGESTED` — still a plausible
  secondary, not rejected. The review card shows every secondary with its
  confidence and rationale, because you cannot judge whether the primary is the
  *right* primary without seeing what it beat.
* **Calibration.** A PROMOTE counts as disagreement in the agreement curve
  (the agent's primary needed changing), same as an EDIT. The frozen
  `mapping_confidence` is the *old* primary's.
* **`exercises.topic_id`** = the primary, as before. Secondaries reach exercises
  via an `exercise_topics` M2M — deferred to M4, which is the first consumer
  ("a topic's chunks = primary OR approved-secondary").
* **Coverage** (`m2/exercise_coverage.md`) now reports two columns: *primarily
  drills* (first-cited requirement) and *also touches* (any). The EXERCISES
  format wants the first. The old single count was a touches count; it is not
  progress that the "5+" number was higher under it.

### 9. Cost — measured, not assumed; prompt caching on

The first six-paper mapping run (2203/2209/2305/2312/2505/2605, threshold 0.80,
no `--review-all`) cost about **$8.75 USD** for ~229 `claude-opus-5` calls —
1.53M input / 110k output tokens, ~6.7k input per chunk. `zaspro.mapping.run`'s
estimator had assumed $15/$75 per 1M and reported $31.19 — **3x high**. Fixed:
the estimator default is now the published `claude-opus-5` rate ($5 input /
$25 output / $0.50 cache-read per MTok, checked 27 Aug 2026), labelled as the
published rate; `--rate-in` / `--rate-out` override it.

**Prompt caching** (`ClaudeMappingAgent.map`): the ~5k-token static prefix —
system prompt + tool schema + the 73-requirement candidate list — carries a
`cache_control: ephemeral` breakpoint, so after the first call of a run each
chunk pays 0.1x for that prefix instead of 1x. That prefix was ~6.2k of the
~6.7k input tokens per chunk, resent 229 times; caching roughly halves the
input bill. `Usage` and the `MAP_CHUNK` job output now carry
`cache_read` / `cache_write` token counts, and the run summary breaks the cost
into fresh / cache-read / cache-write / output.

## What this does not touch

No knowledge extraction, no dedupe/merge, no normalisation, no exercise
generation (M4/M5). `EXTRACTION_CONFLICT` / `NORMALISATION_FAILURE` /
`MERGE_CANDIDATE` review-item types exist in the enum but nothing produces them
yet. `exercise_topics` (secondary topics on exercises) is M4.
