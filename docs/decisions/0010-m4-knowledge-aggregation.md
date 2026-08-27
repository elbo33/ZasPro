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

## Misconception yield check

COMMON_MISTAKES needs five approved misconceptions per topic, and the sources
are thin: exam papers contain none, marking schemes hint through partial-credit
rules, the informator's commentary is the best available. Before extracting all
73, run the knowledge agent on **five** topics, report misconceptions returned
per topic and the source of each, and hold. One or two per topic decides
whether a textbook hunt is needed — cheaper to learn after five API calls than
seventy-three.
