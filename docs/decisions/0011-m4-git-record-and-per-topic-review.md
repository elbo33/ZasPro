# ADR 0011 — M4 simplification: git as record, per-topic review, no misconception suppression

Status: accepted (M4)
Date: 2026-08-28

Supersedes parts of ADR 0010 (the "unsourced misconception is a §11 violation,
kept only to be counted and rejected" rule) and the M4-yield-check framing.

## Context

The first two knowledge runs exposed three problems the aggregation ADR (0010)
did not anticipate:

1. **v2 suppressed real content.** Tightening the misconception prompt
   (v1 → v2) dropped the yield from 18 misconceptions across 5 topics to 7,
   with four of five topics returning zero — and *no* GAP flags, so items were
   being withheld by the agent, not demoted by `extract_topic`. V.4 and III.1
   had each produced five well-evidenced misconceptions in v1 on identical
   input. The "only what the material supports" rule, correct for formulas, is
   wrong for misconceptions: exam papers never state a student error outright.

2. **Nothing irreplaceable should live only in Postgres.** Knowledge specs are
   expensive (a real-agent call per topic) and are meant to be generated once
   and curated. A dropped volume, a bad migration, or `docker compose down -v`
   would lose them.

3. **Review had no home.** M3's queue is mapping-shaped. 73 topics × ~25 items
   is not a queue anyone works item-by-item.

## Decision

### 1. (superseded by §2)

The original v3 decision — "misconceptions emitted, labelled by `source_kind`,
low-provenance ones flagged" — is replaced by §2: every item of every kind
gets a `provenance` label, and it is never a gate.

### 2. A complete spec for every topic, from model knowledge where needed (`m4-know-v5`)

Source material is **not** a constraint on what gets extracted. For every
requirement — including the ~3 with zero mapped exercises and the ~13 with no
primary coverage — the agent produces a full knowledge spec: concepts,
formulas, methods, examples, learning objectives, misconceptions, aimed at
supporting four teaching episodes. It uses the exam exercises where they inform
an item and its own knowledge of Polish high-school mathematics where they do
not. **No suppression, no GAP outcomes, no "insufficient material".** The
progression v1→v5:

* v1–v2 required material support and returned almost nothing for thin topics;
* v3 stopped suppressing misconceptions but still framed non-exam items as a
  deficiency (flagged, GAP rows);
* v4 split the call in two (structure / pedagogy) + added a hard truncation
  check (kept — see §1a);
* **v5**: complete spec for every topic; the only labels are provenance.

Every item — of every kind — records `provenance` (`knowledge_provenance`
enum, migration 0012, on the `_KItem` mixin):

| provenance | meaning |
|---|---|
| `EXAM_TASK` | an exercise informs it (`from_exercises` set) |
| `MARKING_SCHEME` | a Zasady oceniania rule informs it |
| `DISTRACTOR` | a specific multiple-choice option informs it (`Misconception.distractor`) |
| `AGENT_KNOWLEDGE` | the model's own subject knowledge; `from_exercises` empty |

This is **information for the reviewer**, not a gate — a distractor-backed
misconception reads differently from an inferred one. `extract_topic` upgrades a
bare `AGENT_KNOWLEDGE` label to `EXAM_TASK` when a real citation survives, and
never downgrades. `MisconceptionSource` and `misconceptions.source_kind` are
dropped; `distractor` stays. The per-item GAP-flag routing is gone; the
`knowledge_flags` table now carries only genuine CONFLICT flags.

**The human approves every spec in the dashboard. That is the verification
step and the only one that matters.**

### 2a. The empty-exercise-list prompt (fixes the I.5 malformation)

I.5 (0 exercises) produced the `<parameter>` malformation on all three samples —
not bad luck, a degenerate prompt: the user block ended `EXERCISES (0):` with
nothing after it. The raw dumps (`m4/knowledge_debug/`) confirmed it:
`stop_reason: tool_use` (not truncated), **empty `thinking` blocks**, and the
malformation getting *worse* on re-sample (nested `<parameter name="0">`,
integer keys). `_user_block` now emits an explicit "EXERCISES: none — write the
whole spec from the requirement text and your own knowledge; label every item
AGENT_KNOWLEDGE" instead of a dangling header. The `<parameter>` re-sample
logic (§1b) stays as insurance.

No run-to-run variance testing. Extraction happens once, is reviewed, frozen.

### 1a. Streaming, a two-call split, and a hard truncation check (`m4-know-v4`)

The v3 yield check confirmed the approach — 45 misconceptions across five topics
against v1's 18, I.1 from empty to 16 — but exposed two failures:

* **The SDK refuses a non-streaming call whose worst case exceeds ten minutes**,
  which `max_tokens=32000` triggers. `ClaudeKnowledgeAgent` now uses
  `client.messages.stream()` + `get_final_message()`.
* **A large topic still truncated and reported success.** III.1 (23 exercises)
  emitted 11 concepts and then hit `max_tokens` mid-response; `{"concepts":[…]}`
  alone is valid against the schema (every other field defaults to `[]`), so it
  persisted as a complete spec. Two fixes: (a) `extract()` splits into **two
  calls** — `record_structure` (concepts/formulas/methods) then `record_pedagogy`
  (examples/objectives/misconceptions) — so neither response carries a large
  topic's whole spec; (b) each call checks `stop_reason` and raises
  `KnowledgeTruncated` on `max_tokens`, failing the job. `extract_topic` calls
  the agent before `_clear_topic`, so a failed call never touches the stored
  rows. Prompt `m4-know-v4`; the v3 instructions are unchanged, only split
  across the two system prompts.

`zaspro.knowledge.run` gains `--reset` (snapshot every extracted topic to
`m4/reset_backups/<ts>/` then wipe all M4 knowledge rows + KNOWLEDGE_SPEC cards
+ dead EXTRACT_KNOWLEDGE jobs; everything M4 is derived) for a clean `--all`,
and reports per-topic elapsed time and output tokens, names the slowest, and
warns on any topic over eight minutes.

**`--reset` shipped without the snapshot and destroyed 34 topics of completed
extraction with no recovery path** — the second `--all` attempt failed after two
topics and the reset had already run. The snapshot-first behaviour above should
have been there from the start; a wipe of expensive derived data must be
recoverable.

### 1b. Retryable vs permanent job failures; raw-response capture

The first `--all` run hit an **intermittent, sampling-dependent** malformed tool
response: some topics returned `tool_use.input` as a dict whose first field's
*value* was a string of Claude's internal `<parameter name="…">` tool-call
pseudo-syntax instead of a JSON array, so `model_validate` raised
`ValidationError`. Two problems: the job queue retried the *deterministic* error
three times (three identical failures, three paid calls, ~20 min each on a large
topic); and the traceback truncated the offending value, so the shape was
guesswork.

* `zaspro.jobs.PermanentJobError` — the worker fails a job raising it (or a
  subclass) **without** consuming the remaining `max_attempts`. Transient
  failures — connection, timeout, 429, 5xx, overload — propagate unwrapped and
  retry.
* **The `<parameter>` malformation is treated as transient, not permanent.**
  Pydantic is right to reject it; we do **not** build an unpacker for the
  pseudo-syntax — a mis-unpack would produce a silently wrong knowledge spec
  rather than an error. Instead `_parse_call` detects the specific shape (a
  rejected value that is a string containing `<parameter name=`) and raises
  `KnowledgeMalformed` (a plain `RuntimeError`, **not** a `PermanentJobError`).
  `_call` re-samples up to `MALFORMED_RETRIES = 2` times; a retry succeeds
  because it is sampling-dependent (as I.1 did on attempt 2). Only if it
  persists across all three samples does it become a `KnowledgeError`. Every
  occurrence is logged `MALFORMED_TOOL_CALL topic=… tool=… attempt=…` and
  counted into the job output; `run` prints the per-run total so the rate is
  visible. If the rate turns out ~30% rather than ~5%, revisit.
* Genuine schema violations (wrong type, missing required field, no
  `<parameter>` marker) still raise `KnowledgeError` immediately — permanent, no
  retry. So do a missing tool block, a non-JSON string input, a truncation
  (`KnowledgeTruncated`), and an API 4xx other than 429.
* On any parse failure `ClaudeKnowledgeAgent` writes the model's raw content
  blocks (every block's `type`, and for `tool_use` the verbatim `input`) to
  `m4/knowledge_debug/<code>-<tool>-<ts>.json` and names the file in the error.
  `m4/knowledge_debug/` and `m4/reset_backups/` are gitignored.

### 1c. Adaptive thinking is not the cause

The I.5 raw dumps show **empty `thinking` blocks** on every malformed sample, so
interleaved thinking was not implicated — the cause was the degenerate empty
prompt (§2a). `ClaudeKnowledgeAgent` still takes `thinking: bool = True` and
`run` has `--no-thinking` for a cost/quality comparison, but the retry logic
(§1b) stays as insurance, not as the fix.

### 3. One `KNOWLEDGE_SPEC` review card per topic

A single `ReviewItem` (`item_type = KNOWLEDGE_SPEC`, `ref_table = "topics"`,
`ref_id = topic_id`) carries the whole spec. `record_decision`:

* **APPROVE** — every knowledge item not individually rejected →
  `verification_status = APPROVED`; card resolved.
* **REJECT** (reason required) — every item → `REJECTED`; flags resolved; the
  spec is thrown out.
* **EDIT** — `edit = {"reject_items": [["misconception", 12], …]}` (and
  `"unreject_items"`) toggles individual items and leaves the card OPEN for a
  follow-up APPROVE.

`knowledge_extractions` (migration 0011) is one row per topic: the last
extraction (`agent_name`, `model`, `prompt_version`, `exercises`,
`extracted_at`), the guarding `review_item_id`, and `approved_at` /
`approved_by` / `exported_at` / `export_path`. Re-extraction reuses and reopens
the card; prior `review_decisions` are immutable history.

Dashboard: a `/knowledge` index (one row per requirement, counts + review /
export state) and a `KNOWLEDGE_SPEC` branch on the review card — keys `a`
(approve), `E` (approve & export), `x` (reject/restore the selected item),
`j`/`k` (move), `r` (reject spec), `s` (skip).

### 4. Git holds the record, the database is the working store

An approved topic exports to **`knowledge/topics/<official_requirement_code>.yaml`**
— human-readable, diffable, one file per topic. It carries the extraction
metadata, every APPROVED item with its evidence and cited `from_exercises`, the
unresolved flags, and the touch-set exercise index (numbers + source document,
not full text — that lives in the source documents M2 re-ingests).

`export_topic` refuses while the topic's review card is OPEN (or REJECTED). Once
written, **the committed file is the freeze**: `extract_topic` raises
`KnowledgeFrozen` for a topic that has one unless `force=True` (which then
requires re-review and re-export). Nothing overwrites a committed spec silently.

The database should be rebuildable from git (`knowledge/`, `sources/`, the
migration chain) plus the source documents. `scripts/backup.sh` (dump to
`backups/`, dated, gitignored) and `scripts/restore.sh` are convenience only;
the README notes `docker compose down -v` destroys the volume.

## Consequences

* `zaspro.knowledge.run --all` extracts every podstawowy requirement, prints a
  cost estimate and asks before spending, and reports queue depth afterwards.
* `zaspro.knowledge.export --all` freezes every topic whose card is resolved.
* The v1 finding that thirteen requirements have no primary coverage (ADR 0010)
  still stands; I.1's "31 touch exercises → formulas but nothing teachable"
  remains the argument for the teaching layer absorbing them. Under v3 those
  topics will produce misconceptions again (labelled `AGENT_INFERENCE` /
  `UNSOURCED`), so the teaching-layer decision is now about episode structure,
  not about whether any content exists.
* `MisconceptionSource.UNSOURCED` is no longer "a §11 violation kept only to be
  rejected" — it is a valid, flagged label the reviewer rules on.
