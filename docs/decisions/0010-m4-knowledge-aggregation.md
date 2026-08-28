# ADR 0010 — M4 knowledge aggregation: exercise_topics, stem-inclusive text

Status: accepted (M4, opening)
Date: 2026-08-28

## Context

M4 aggregates per topic from its mapped chunks and extracts concepts, formulas,
methods, examples, objectives, misconceptions (SPEC §11). Three things had to be
settled before the knowledge agent runs, not after.

## 1. `exercise_topics` is materialised before extraction

`exercise_topics` (migration 0008): `(exercise_id, topic_id)` PK, `role ∈
PRIMARY | SECONDARY`, `confidence`, `source_chunk_mapping_id` for provenance.

`zaspro.knowledge.aggregate.rebuild_exercise_topics` builds it from
`chunk_mappings`: for each exercise, find its `source_chunk`, take that chunk's
**primary** mapping — if it is `AI_SUGGESTED` (auto-approved at or above
`AUTO_APPROVE_THRESHOLD = 0.70`) or human `APPROVED`, emit a PRIMARY row for its
topic and a SECONDARY row for every other topic the chunk's mappings name.
Chunks whose primary mapping is `REJECTED` or still `REVIEW_REQUIRED` are
skipped entirely (unsettled).

**Why materialised, not a view:** the knowledge agent reads a fixed, reviewed
set; re-running the aggregation is explicit (`zaspro.knowledge.coverage_run`)
and its output is diffable. It is rebuilt whenever mappings change.

**Aggregation is over the touch set (PRIMARY ∪ SECONDARY), not PRIMARY alone.**
Extracting from primaries only would rebuild the single-topic view that
multi-topic mapping (ADR 0009 §8) removed — Zadanie 13 drills V.6 but also V.5;
V.5's knowledge spec must see it.

### Coverage under both definitions (28 Aug 2026)

263 exercises carry topics (263 PRIMARY + 416 SECONDARY rows; 3 skipped for an
unsettled primary mapping — the three human rejections). Over the 73 podstawowy
requirements:

| exercises per requirement | primary | touch |
|---|---|---|
| 0 | 13 | 3 |
| 1–2 | 20 | 8 |
| 3–4 | 15 | 9 |
| **5+** | **25** | **53** |

Covered (≥1): **60/73 primary, 70/73 touch**. The EXERCISES format's 5-per-topic
bar is met for **25** requirements on the primary definition, **53** on touch.
The gap is the point of the touch set: it roughly doubles the well-covered
requirement count, and that is the material the knowledge specs get built from.
(`m4/topic_chunk_coverage.md`.)

## 2. Exercise text is read stem-inclusive, always

The M3 stem defect was `map_chunk` reading `chunk.text` (a subtask's own body)
while the shared setup lived on the parent. M4 knowledge extraction has the same
shape. Rule: **read `Exercise.full_statement` (plain) or
`Exercise.full_statement_latex` (raw LaTeX), never `Exercise.statement` /
`SourceChunk.text` alone.** `full_statement_latex` was added in this change.

Audit of every current text reader:

| site | reads | verdict |
|---|---|---|
| `api/views.py` review card | `chunk.text` + `chunk.latex`, and now `chunk_stem` from `_parent_chunk` | OK — stem shown separately (M3 fix) |
| `mapping/handler.py` `map_chunk` | `chunk.text`/`latex` + parent `text`/`latex` as `stem` | OK — M3 fix |
| `ingestion/persist.py` | writes `SourceChunk.text` / `Exercise.statement` = the task's own body | OK — this is the write side; stem is composed at read time by design |
| `knowledge/aggregate.py` | topics/mappings only, no exercise text | OK |

No M4 code reads exercise text yet; when it does it must use the `full_*` forms,
and this ADR is the reference.

## 3. One requirement ≠ one episode

`official_requirement_code` is the legal definition of what is examinable, not a
teaching unit. Episodes will be generated from a **teaching layer** above the
requirements — grouping via `topics.parent_id`, requirements kept as `parent_id`
children with their code — built as work **between M4 and M6** (SPEC §17). M4
must not assume a 1:1 requirement→episode mapping anywhere; knowledge specs are
per requirement, and how requirements combine into an episode is not M4's
concern. Not built, not designed around here — just not assumed.

## 4. The Knowledge Agent

`zaspro.knowledge.agent` follows the ADR 0009 shape: a `KnowledgeAgent`
Protocol, `ClaudeKnowledgeAgent` (`claude-opus-5`, adaptive thinking, one
structured tool `record_knowledge`, prompt-cached system + tool), and an offline
`StubKnowledgeAgent`. One call per topic returns a `KnowledgeExtraction` —
concepts, formulas, methods, examples, misconceptions, objectives, and CONFLICT
/ GAP flags.

Input per topic (`zaspro.knowledge.extract.topic_exercises`): the requirement
text plus every exercise in the `exercise_topics` touch set, each as
`Exercise.full_statement_latex` (stem + body) with its `Zasady oceniania`
partial-credit block where the session's zasady PDF has one.

Business rules re-checked in `extract_topic` (SPEC §11/§12, never LLM →
database):

* an item's `from_exercises` are resolved (`refs()` — number tokens out of each
  entry, prose fallback) against the topic's real exercise numbers;
  `source_chunk_ids` is the chunk ids of the survivors.
* a misconception the agent tags `AGENT_INFERENCE` **or**
  `DISTRACTOR_INFERENCE` with **no** surviving exercise citation is stored as
  `UNSOURCED` and raises a `knowledge_flags` GAP row — an unsourced
  misconception is a §11 violation, kept only so it can be counted and
  rejected, not approved. `MARKING_SCHEME` / `INFORMATOR` /
  `DISTRACTOR_INFERENCE` that do cite a task are kept as-is.
* `flags` become `knowledge_flags` rows (later: review items).

`extract_topic` clears the topic's prior knowledge items first, so re-running is
idempotent.

## Misconception yield check

COMMON_MISTAKES needs five approved misconceptions per topic, and the sources
are thin: exam papers contain none, marking schemes hint through partial-credit
rules, the informator's commentary is the best available (and is not ingested
yet). Before extracting all 73:

`zaspro.knowledge.run --topics 5` picks a **deliberate spread** — two
requirements well covered under *touch* and with primary coverage, two mid
(touch 3–4), one of the requirements with **no primary** exercise — then runs
extraction and reports, per topic: the concept/formula/method/example/objective
counts and **every misconception with its `source_kind`
(`MARKING_SCHEME | INFORMATOR | DISTRACTOR_INFERENCE | AGENT_INFERENCE |
UNSOURCED`), the exercises it cites, the distractor where it has one, and the
evidence snippet**; then holds. The deliberate spread answers "does yield track
material volume, or is it uniformly thin"; the per-source breakdown answers "is
this a misconception database or the model's priors". If most come back
`AGENT_INFERENCE` / `UNSOURCED`, the marking schemes / a textbook need ingesting
before COMMON_MISTAKES is viable — learned after five API calls, not
seventy-three. The run is a command the user executes (standing rule).

### First run (28 Aug 2026) — two findings

**Citation bug (fixed).** Every stored item read `from Zadanie none` although
its `evidence` prose named the task. `extract_topic` intersected the agent's
`from_exercises` with the topic's exercise numbers by exact string match; the
real agent returns `"Zadanie 11.1"` / `"Zad 11.1 dystraktory B and D"`, or
leaves `from_exercises` empty and names the task only in prose. Nothing was
traceable in the database — a §11 provenance failure regardless of source
category. Fix: `refs()` pulls every number token out of each `from_exercises`
entry, and falls back to scanning the item's own prose behind a `Zad`/`Zadanie`
marker when the field is empty. Schema fields now carry descriptions asking for
bare numbers. `PROMPT_VERSION` → `m4-know-v2`.

**`DISTRACTOR_INFERENCE` added to `MisconceptionSource`** (migration 0010:
`misconceptions.distractor` column + `source_kind` widened to VARCHAR(32); the
enum has no CHECK). Most items the first run tagged `UNSOURCED` were not
invention — each cited a specific multiple-choice distractor in a named exercise
(*"Zad 11.1 dystraktory B and D"*, *"Zadanie 14 dystraktor C: 20000 · 1,06"*).
CKE builds each wrong option to catch a particular error, so a distractor is a
real source — likely the richest one the corpus offers. The agent now records
the task in `from_exercises` and the option(s) in `distractor`; `extract_topic`
keeps it as a real source when a task is cited and demotes it to `UNSOURCED`
only when nothing is. The yield split counts `MARKING_SCHEME + INFORMATOR +
DISTRACTOR_INFERENCE` as "from a real source".

### I.1 is the informative failure

I.1 (`liczby rzeczywiste`) has **no primary exercise** and 31 in the touch set.
The first run drew 10 concepts and 13 formulas from it — and 0 examples, 0
learning objectives, 0 misconceptions. Aggregating exercises that merely *use* a
requirement yields its formulas and vocabulary and nothing teachable: no worked
example is *about* I.1, no marking scheme grades I.1 specifically, no distractor
targets an I.1 error. **A requirement with no primary coverage cannot support an
episode on touch alone.** There are **13** such requirements (ADR table above).
This is a concrete argument for the teaching layer (§3, SPEC §17) absorbing them
— folded into a parent teaching unit that does have primary material — rather
than each of the 13 being scoped as its own episode with a knowledge spec built
from formulas alone.
