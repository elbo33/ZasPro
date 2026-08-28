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
