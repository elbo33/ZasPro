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

### 1. Misconceptions are emitted, labelled, and flagged — never suppressed

The agent lists every real, common student error on the requirement (aim 3–6)
and labels each with `source_kind`:

| source_kind | meaning | provenance |
|---|---|---|
| `MARKING_SCHEME` | a partial-credit / "0 pkt jeśli…" rule | real |
| `INFORMATOR` | CKE informator commentary (not ingested yet) | real |
| `DISTRACTOR_INFERENCE` | a named multiple-choice distractor built to catch it | real |
| `AGENT_INFERENCE` | inferred from an open exercise's structure | needs review |
| `UNSOURCED` | a known error with nothing in the material behind it | needs review |

`extract_topic` relabels an `AGENT_INFERENCE` / `DISTRACTOR_INFERENCE` claim
with no surviving exercise citation as `UNSOURCED` (accurate labelling, not
suppression), and raises a `knowledge_flags` GAP row for every `AGENT_INFERENCE`
and `UNSOURCED` misconception. **Human approval in the dashboard is the
verification step** — an AI-inferred misconception is acceptable once a person
has approved it. Concepts / formulas / methods / examples / objectives keep the
strict SPEC §11 rule: only what the material shows.

Prompt is `m4-know-v3`. `max_tokens` raised 16k → 32k (v2 was truncating output
on the large topics; v3 asks for more).

No run-to-run variance testing. Extraction happens once, is reviewed, and is
frozen (§3). Variance does not matter if we never re-run.

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

### 1b. Retryable vs permanent job failures; raw-response capture

The first `--all` run hit an **intermittent** malformed tool response: some
topics returned `tool_use.input` as a dict whose first field's *value* was a
string of XML-style `<parameter name="…">` tags instead of a JSON array, so
`model_validate` raised `ValidationError`. Two problems: the job queue retried
it three times (deterministic → three identical failures, three paid calls,
~20 min each on a large topic); and the traceback truncated the offending
value, so the actual response shape was guesswork.

* `zaspro.jobs.PermanentJobError` — the worker fails a job raising it (or a
  subclass) **without** consuming the remaining `max_attempts`. `KnowledgeError`
  and `KnowledgeTruncated` are subclasses; schema-invalid input, a missing tool
  block, a non-JSON string input, and a 4xx (other than 429) from the API all
  raise `KnowledgeError`. Transient failures — connection, timeout, 429, 5xx,
  overload — propagate unwrapped and are retried.
* On any parse failure `ClaudeKnowledgeAgent._call` writes the model's raw
  content blocks (every block's `type`, and for `tool_use` the verbatim
  `input`) to `m4/knowledge_debug/<code>-<tool>-<ts>.json` and names the file
  in the error. The parse itself is unchanged pending that evidence —
  no tag-stripping heuristic. `m4/knowledge_debug/` and `m4/reset_backups/`
  are gitignored.

### 2. One `KNOWLEDGE_SPEC` review card per topic

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

### 3. Git holds the record, the database is the working store

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
