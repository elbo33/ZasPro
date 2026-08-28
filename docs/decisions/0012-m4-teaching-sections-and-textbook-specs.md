# ADR 0012 — M4 rebuilt: teaching sections, textbook-style specs, exercises out

Status: accepted (M4)
Date: 2026-08-28

Supersedes the exercise-based knowledge layer of ADR 0010 and 0011. Migrations
0008–0012 built a pipeline that aggregated exam exercises per requirement and
extracted knowledge from them. It produced almost nothing for thin requirements,
its provenance machinery never earned its keep, and debugging its edge cases
(truncation, `<parameter>` malformation, retry taxonomies) cost real money and
shipped no reviewable knowledge. Torn out.

## Decision

### 1. A teaching tree, seeded from the requirements

`sections` + `section_requirements` (migration 0013), seeded from
`seeds/teaching_sections.yaml` (proposed in `m4/teaching_tree_proposal.md`,
approved). **62 lesson-sized sections** (50 → 58 with a theorem-split pass →
62 after splitting X.5 by solid type and III.4 into equations vs inequalities),
ordered in teaching sequence, each covering one or more
`official_requirement_code`s. `seed_sections` asserts every podstawowy
requirement is covered by **at least one** section — a requirement may span
several sections (X.5's five solids, III.4's equations vs inequalities), all
keeping the same code; the guarantee is coverage, not a partition. Sections are
the "teaching layer above requirements" flagged in
SPEC §17 / ADR 0010 §3; requirements remain the legal definition of what is
examinable.

### 2. The agent writes each section as a textbook would

`ClaudeSectionAgent.write(section)` — one call, one tool (`record_section`),
`claude-opus-5`, streaming, `max_tokens=64000`. Input is the section name, its
scope line, and the text of the requirements it covers. Output:

* concepts — every definition and idea a student needs, with how to think about it;
* formulas — with the conditions under which they hold;
* methods — the standard procedures, with when to use each and ordered steps;
* examples — worked in full, ordered to build in difficulty;
* misconceptions — the mistakes students actually make, with the correction;
* objectives — what a student should be able to do, at the right Bloom level.

Written from the model's knowledge of Polish Matura podstawowa mathematics,
bounded by the scope. **Exercises are not a source** — no aggregation, no
citation, no "a section with no exam tasks gets a thinner spec". No provenance
labels, no `source_kind`, no flags: everything is agent-written and
human-approved, so there is nothing to distinguish.

### 3. No retry logic, no failure taxonomy

If a section's call fails — no tool call, unparseable output, an API error — the
job fails, `zaspro.knowledge.write` prints the last error line, and the run
moves on. Re-run that section by slug. `PermanentJobError` /
`KnowledgeMalformed` / `KnowledgeTruncated` / the `<parameter>` re-sampler / the
raw-response dumper are all gone.

### 4. One review card per section; approved specs freeze to git

A `KNOWLEDGE_SPEC` `ReviewItem` per section (`ref_table = "sections"`).
`record_decision` APPROVE marks every non-rejected item `APPROVED`, REJECT
throws the spec out, EDIT (`reject_items` / `unreject_items`) toggles individual
items. `section_specs` is one row per section (last write + approval/export
state). Approved sections export to
**`knowledge/sections/<slug>.yaml`** — human-readable, diffable, one file per
section; the committed file is the freeze (`write_section` refuses to re-run a
section that has one without `force=True`).

### Schema changes (migration 0013)

* new `sections`, `section_requirements`
* the six knowledge item tables: `topic_id` → `section_id`; drop `provenance`,
  `source_chunk_ids`, and `misconceptions.distractor`; `order_index` on all six
* drop `knowledge_flags`
* `knowledge_extractions` → `section_specs` (section-keyed, `written_at`)
* `KnowledgeProvenance`, `MisconceptionSource`, `FlagKind`, `KnowledgeFlag`
  removed from the models
* `exercise_topics` and `zaspro.knowledge.aggregate` are left in place but
  unused by the knowledge path (an M3 artefact; possibly useful to M5)

## Consequences

* `uv run python -m zaspro.knowledge.write --all` writes all 62 sections
  (~$25–45 at opus-5 rates; ~14–24k output tokens per section). It cleans up
  pre-0013 leftovers (topic-scoped cards, stale jobs) on startup.
* `uv run python -m zaspro.knowledge.export --all` freezes the approved ones.
* **Not now (M5):** exercise generation, verification, normalisation. The
  section spec has no fields for them and nothing is built toward them.
