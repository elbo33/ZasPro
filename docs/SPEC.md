# ZasPro: Polish Matura Knowledge Base and Episode Planning System

Authoritative specification. Version 3, 26 August 2026.

Supersedes all earlier drafts. Where this document and any other file disagree, this document wins.

---

## 0. ROLE AND SCOPE

You are the primary engineer for a system that turns official Polish Matura source material into a verified, structured educational knowledge base, and then into episode and scene plans.

**This project stops at the scene plan.** A separate system, developed independently, consumes scene plans and produces video. You are building the upstream half.

### IN SCOPE

* source ingestion and document processing
* curriculum modelling
* knowledge extraction with provenance
* exercises, formulas, misconceptions
* mathematical verification where automatable
* human review and approval tooling
* episode planning and scene planning
* the Scene Spec JSON contract consumed by the external renderer
* job system, dashboard, tests

### EXPLICITLY OUT OF SCOPE

Do not build, stub, scaffold, install dependencies for, or design around:

* Manim or any animation code generation
* text-to-speech, audio files, audio duration measurement
* video rendering, ffmpeg, subtitles, thumbnails
* YouTube API, uploads, playlists, scheduling, analytics
* any object storage for video or audio artifacts

If a design decision seems to require one of these, stop and write the assumption into `docs/decisions/` instead of implementing it.

The deliverable at the far end of this pipeline is a validated JSON scene plan sitting in the database, ready for a renderer that does not exist in this repository.

---

## 1. GUIDING PRINCIPLES

```text
KNOWLEDGE FIRST
CONTENT SECOND
EVERYTHING ELSE IS SOMEONE ELSE'S PROBLEM
```

1. The database is the long-term asset. Episode plans are one consumer of it.
2. Every fact traces back to a source, with page and section references intact.
3. Nothing AI-generated enters the verified knowledge base without either programmatic verification or human approval.
4. Uncertainty is recorded, never silently resolved.
5. Build the smallest thing that exercises the full path, then widen it.

---

## 2. SETTLED DECISIONS

These follow from a source-and-tooling research pass and an extraction spike completed 26 August 2026. They are decided. Do not reopen one without telling me why.

1. **The curriculum ground truth is the 2024 podstawa programowa** (Dz.U. 2024 poz. 1019), not the `wymagania egzaminacyjne`. The latter applied only to the 2023 and 2024 exams and is superseded. Many secondary sources still cite it. Do not seed from a secondary source or from model recollection.
2. **Formuła 2023 only.** Formuła 2015 material is recorded in the source manifest but not ingested. Revisit only if exercise volume becomes a constraint.
3. **Verbatim source text is stored**, with `verbatim_ok = false` by default. Publishable derivatives are separate rows carrying their own provenance. Storage and publication are distinct concerns and the schema must keep them distinct.
4. **Parallel paper versions (A/B) are separate exercise rows**, joined by `variant_group_id`. Deduplication must never merge across a variant group.
5. **The `zasady oceniania` marking scheme is both a validation oracle and a knowledge source.** It independently enumerates every exercise with point values, and its partial-credit breakdown maps onto `solution_steps`.
6. **Exercise boundary recovery outranks formula fidelity.** An exercise with a slightly imperfect equation is repairable. An exercise whose boundaries dissolved into the next one is not.
7. **Extraction from CKE material is deterministic, not model-based.** See section 2a. Pandoc converts the DOCX accessibility exports directly.
8. **Rendered LaTeX and parseable LaTeX are different artifacts.** See section 2a and section 7. Never feed display LaTeX to a solver without normalisation.
9. **Podstawowy only, for now.** Settled 27 Aug 2026 after the M2 corpus went in. Every Matura candidate sits the podstawowy exam; the deterministic Track A path works end to end for it (3/3 corpus arkusze pass with no fixing round). Rozszerzony has **no czarnodruk DOCX in any Formuła 2023 session** — it is entirely Track B (PDF, non-deterministic), which stays deferred (ADR 0005). A complete single-level course beats a half-populated two-level one. The 46 rozszerzony topics stay in the curriculum tree, seeded and correct, carrying no content; the rozszerzony informator and arkusze stay in the manifest as future material. See ADR 0008.

10. **The deterministic corpus is calibration and seed material, not supply.** Settled 27 Aug 2026 after the exercise-coverage histogram over seven Track A sessions (`m2/exercise_coverage.md`): the 5-exercise-per-topic bar the EXERCISES episode format needs is met for 22 of 73 podstawowy requirements, and CKE publishes only ~2 podstawowy sessions a year, so harvesting alone will not close the gap on any useful horizon. The harvested arkusze anchor difficulty, phrasing and Matura-authentic style; **the Exercise Agent (M5) is load-bearing for the EXERCISES format, not a supplement.** For most topics the exercises used by an episode will be generated-and-verified, not harvested. Scope M5 to that: generation + symbolic verification is the primary path, marking-scheme cross-check applies only to the harvested minority. See section 13.

The verified source inventory and extraction tooling research live in `docs/sources.md`. Read it before M0.

---

## 2a. SPIKE RESULTS

Measured, not assumed. These numbers are the basis for M0 and for several decisions above.

| document | oMath | display (`oMathPara`) | drawings | media files |
|---|---|---|---|---|
| `Informator_EM2024_matematyka_pp_660.docx` | 994 | 212 | 25 | 0 |
| `MMAP-P0-660-A-2605-arkusz.docx` | 284 | 9 | 18 | 5 |

Corrected 2026-08-26 during M0.1. The original figures (informator 1386 / 392;
arkusz oMath 298) came from a raw `<m:oMath` substring count, which also matches
the `<m:oMathPara` and `<m:oMathParaPr` prefixes, so display equations and
paragraph-property elements were folded into the `oMath` column. The table now
holds element counts from `word/document.xml` matching `<m:oMath[ >]` and
`<m:oMathPara[ >]`, open/close tags verified balanced. Old minus new checks out:
`1386 − 392 = 994`, `298 − 14 = 284`. The corrected numbers do not change any
decision in section 2 or the M0 plan; the "carries a lot of native OMML"
finding is unaffected.

Findings:

1. **CKE's `_660.docx` accessibility exports carry native OMML mathematics.** Not images, not flattened text. The transform to LaTeX is deterministic.
2. **Pandoc 3.10.2 converts both files correctly.** Polish diacritics survive intact, hyperlinks are preserved, equations are accurate.
3. **Exercise structure survives as parseable text**: `Zadanie N. (0--M)` with point values inline, subtasks as `Zadanie N.M. (0--M)` under an unpointed parent heading that carries the shared stem.
4. **Task figures are Word-drawn shapes, one route not three.** Measured in M0.4 across the maj-2024/2025/2026 `_660.docx` files and **re-verified 27 Aug 2026 across all seven Track A papers** (2203, 2209, 2305, 2312, 2405, 2505, 2605): every figure attached to an exercise is a `<w:drawing>` DrawingML shape, which pandoc drops silently. The raster (`.jpeg`, `.png`) and vector (`.wmf`) media in `word/media/` — including the older papers' — are all page furniture: cover security notice, running-footer graphic, header barcode. Never an exercise figure. The recovery route that matters is DOCX→PDF via LibreOffice plus region cropping. `RASTER` (`--extract-media`) and `WMF` (LibreOffice) handlers exist and are wired to `source_format` for a future source, but no exercise in this corpus needs them. One caveat the seven-paper pass added: a `<w:drawing>` with **no substance** — no image, no text box, only a few bare connector lines — is *not* a figure and must not inflate `expected_figure_count` (2312 Zadanie 11.4 is such a stray group on a text-only question). See section 5 and M0.4.
5. **Pandoc's LaTeX is visually faithful and semantically unsafe.** Real output from Zadanie 4:

   ```latex
   \log_{8}{4 - \log_{8}32}
   ```

   This renders as log₈4 − log₈32, which is correct. Parsed as an expression it reads as log₈(4 − log₈32), which is not. The grouping braces are invisible when rendered and wrong when evaluated. It fails silently in exactly the place that matters.

6. **Naive-parse failure rate: 37%** (M0.3, `m0/normalisation_study.md`). 30 equations sampled from 314 structured ones across both conversions, stratified over fractions, radicals, logs, powers, systems/piecewise and `\text{}`-wrapped forms, three named cases pinned. Each fed raw to `sympy.parsing.latex.parse_latex(backend="lark")` with no normalisation:

   | class | count | nature |
   |---|---|---|
   | OK | 19 | parses to the intended expression (rationalisation / eager eval is value-equal) |
   | PARSE_ERROR | 7 | does not parse — **fails loudly**, ordinary normaliser work |
   | NOT_MACHINE_CHECKABLE | 2 | notation, not an expression (set literals, `\|BC\|` segment length) |
   | AMBIGUOUS | 1 | parser returns an unresolved `_ambig` tree (`\log{K(t)}`) |
   | WRONG_SILENT | 1 | parses to a **different** expression with no error — the `\log_{8}{…}` case |

   **11/30 do not yield the intended expression.** Only the single WRONG_SILENT case is dangerous: it is the one that reaches a solver looking correct. The 7 parse errors and 1 ambiguity fail visibly and route to review by construction; handling them is the normalisation layer's normal job, not a threat. M5's scope and its auto-verification-rate expectations derive from this number.

7. **`pdftotext` corrupts maths in the podstawa programowa PDF, silently** (M0.5, `m0/pdf_audit.md`). `DU_programowej_2024.pdf` and the superseded `matematyka.pdf` set their maths in a font whose ToUnicode maps each Mathematical Alphanumeric Symbol (U+1D400–U+1D7FF, the italic variables) to a **two-codepoint sequence**: 54% and 56% of math-italic characters come out **doubled** (`𝑥𝑥` for `𝑥`). Stacked fractions and superscripts collapse with it — measured examples from the curriculum text: `½·a·b·sin γ` → `2·a·b·sin γ` (halving becomes doubling), `f(x) = a/x` → `f(x) = x` (coefficient gone), `sin α / cos α` → `cos α` (numerator gone). The M0.5 diacritic check passed on the same files because the **prose** font has a correct ToUnicode — the two live in one PDF. Consequence: the M0.6 curriculum seed's formulae are hand-transcribed from the rendered PDF (`seeds/curriculum_matematyka_formulas_review.md`), and `topics.statement_latex` (section 5) exists to hold them separately from the prose. Any Track B source must pass the math-character assertion before M2 text-mines it.

Consequence: rendering is the correct check for extraction fidelity and the wrong check for verification input. These are separate concerns needing separate artifacts. The normalisation layer (M5) must convert a documented ~37% of raw expressions before they are trustworthy, and must never let a WRONG_SILENT parse through unflagged.

---

## 3. STACK

* **Python 3.12** owns the schema, migrations, ingestion, extraction, verification, and job execution. Document parsing and symbolic maths are Python-native and this is not negotiable.
* **PostgreSQL 16** as the single source of truth. `pgvector` is added only when a retrieval task actually needs it, not in the first migration.
* **Alembic** for migrations. One migration system only.
* **SQLAlchemy 2.x** typed ORM models, modern declarative style with `Mapped[]` annotations and a `type_annotation_map` for reused domain types.
* **Pydantic v2** for all AI input and output schemas and all ingestion contracts.
* **FastAPI** for the internal API.
* **Pandoc** for DOCX to LaTeX conversion, invoked as a subprocess. Do not build a custom OMML converter; see section 2a.
* **LibreOffice headless** — M0.4 confirmed it. It is the primary figure route: DOCX→PDF, then crop the `WORD_SHAPE` region. Also handles WMF. Not optional.
* **A job runner**: start with a Postgres-backed queue table plus a worker loop. Do not add Celery, Redis, or RabbitMQ until the simple version is provably insufficient.
* **Next.js (App Router) dashboard**, read-mostly, calling the FastAPI backend. The dashboard does not own or migrate the schema and does not talk to Postgres directly.
* **Local filesystem** for source documents, extracted media, and rendered images in development, behind a storage interface with an S3-compatible implementation available.

Secrets in environment variables. Expected: `DATABASE_URL`, `ANTHROPIC_API_KEY`, `STORAGE_ROOT`. Nothing else yet.

### Dependency licensing

Before adding any extraction dependency, record its licence in `docs/decisions/dependencies.md`. Two to verify carefully against the project's own repository rather than a summary:

* PyMuPDF is AGPL-3.0 with a commercial option
* some datalab.to projects attach revenue conditions to otherwise open licences

This project may eventually carry paid content, so licence terms are load-bearing rather than paperwork.

---

## 4. SOURCE PRIORITY AND COPYRIGHT

Sources are seeded in this order, which is also the conflict-resolution hierarchy:

1. The 2024 podstawa programowa (Dz.U. 2024 poz. 1019)
2. Official CKE materials (`informatory`, formula sheet)
3. Past exams and marking schemes (`arkusze`, `zasady oceniania`)
4. Verified open educational resources
5. Licensed textbooks
6. Other material
7. AI-generated material

AI-generated material never overrides anything above it without human approval.

### Copyright handling

Source material and generated material are different things and must be distinguishable in the database at all times.

Source text may be used to understand curriculum coverage, terminology, difficulty calibration, exercise categories, and standard approaches. Every content row carries an `origin` and a `verbatim_ok` flag. Content with `verbatim_ok = false` is never eligible for downstream publishable output, regardless of how it is referenced.

Regulations published in Dziennik Ustaw are `materiały urzędowe` and fall outside copyright. The status of exam papers is less settled, and papers may embed third-party figures whose rights sit elsewhere. Encode this in data, not in a comment, and default to the restrictive setting.

---

## 5. DATA MODEL

Design the full schema up front but **create tables in migration batches per phase**, so early migrations stay reviewable.

### Curriculum

* `subjects`: id, name, slug, description, language, level, timestamps
* `units`: id, subject_id, name, slug, description, order_index
* `topics`: id, unit_id, parent_id, name, slug, description, statement_latex, level, order_index, official_requirement_code, status, timestamps
* `topic_prerequisites`: topic_id, prerequisite_topic_id, importance, reason

`official_requirement_code` is the link back to the podstawa programowa numbering and is unique where present.

**`name` / `description` hold prose only; `statement_latex` holds the maths.** A podstawa requirement often embeds a formula (`aˣ < aʸ`, `½·a·b·sin γ`, the binomial-coefficient identities). The prose part — the verb, the scope — goes in `name`/`description` in plain text with single-letter variables as ordinary italics. The formula goes in `statement_latex` as valid LaTeX. This split exists because the seed's own source proved extraction cannot be trusted for it: `DU_programowej_2024.pdf` sets its maths in a font whose ToUnicode doubles every italic variable (`𝑥𝑥` for `𝑥`) and collapses stacked fractions, so `pdftotext` turned `½·a·b` into `2·a·b` and `sin α / cos α` into `cos α` — plausible, wrong, silent (M0.5, `m0/pdf_audit.md`). `statement_latex` is therefore hand-transcribed from the rendered PDF, not extracted; a `NULL` value means the requirement carries no formula.

`statement_latex` follows a fixed notation convention (`m0/curriculum_notes.md`): explicit sized delimiters (`\left|…\right|`, never bare pipes — the M0.3 study showed a parser misreads them), `\frac` not inline slashes, `\sqrt[n]{}`, `\binom{n}{k}`, Polish `\tg`/`\ctg` not `\tan`/`\cot`, `\cdot` for explicit multiplication. `\tg` and `\ctg` are not standard LaTeX; any renderer consuming `statement_latex` (or the Scene Spec's raw-LaTeX fields, section 6) must `\DeclareMathOperator` them in its preamble.

**Representation.** Adjacency list with a `parent_id` self-foreign-key. The tree is small, shallow and effectively read-only after seeding, so the performance arguments for materialized paths and `ltree` do not apply. Adjacency is the only representation where reparenting is a single-row update that cannot leave the tree inconsistent. Add a generated materialized path column later if the same recursive CTE gets written repeatedly. Consider `ltree` only if its pattern-matching operators are wanted, which is a different motivation from performance.

**Prerequisites** are a separate structure: a DAG over topics and concepts, not a tree over curriculum sections. Do not conflate them. Enforce acyclicity at write time using PostgreSQL's `CYCLE` clause (`CYCLE id SET is_cycle USING cycle_path`, available since PG 14) rather than trusting the seeding process. Prerequisite edges are the rows most likely to be added by hand or inferred by a model, and therefore the rows most likely to introduce a loop.

### Sources and provenance

* `sources`: id, title, author, publisher, year, source_type, licence_status, verbatim_ok, reuse_notes, url, file_ref, notes, processing_status
* `source_documents`: id, source_id, file_ref, page_count, extraction_status, variant_code, paper_version, session_code, sibling_docx_ref
* `source_chunks`: id, source_document_id, page, chapter, section, heading, content_type, text, latex, order_index, extraction_method, confidence
* `figures`: id, source_document_id, page, bbox, image_ref, source_format, render_status, caption

`source_type` ∈ `PODSTAWA_PROGRAMOWA | OFFICIAL_CKE | EXAM | MARKING_SCHEME | FORMULA_SHEET | TEXTBOOK | OPEN_EDUCATIONAL_RESOURCE | USER_PROVIDED | OTHER`

`content_type` ∈ `EXPLANATION | DEFINITION | FORMULA | EXAMPLE | EXERCISE | SOLUTION | THEOREM | NOTE | WARNING`

`extraction_method` ∈ `pandoc_omml | pdf_text | pdf_vision | manual`

`source_format` on figures ∈ `RASTER | WMF | WORD_SHAPE`, and it selects the extraction path (M2, `zaspro.ingestion` figure handlers):

* `WORD_SHAPE` — a DrawingML shape or shape group with no embedded media. Pandoc drops it silently; recover by rendering the DOCX to PDF via LibreOffice and cropping the task's region with pdfplumber vector primitives. **Every exercise figure in the seven-paper Track A corpus is this** (SPEC §2a finding 4), and it fails in the most ways (see `docs/decisions/0004-figure-routes.md`).
* `RASTER` — `<w:drawing>` embeds a bitmap (`<a:blip r:embed>` → `word/media/…`). Copy the media file out. Present only as page furniture in this corpus; the handler exists for a future source.
* `WMF` — embeds a metafile (`.wmf` / `.emf`). Convert to PNG with LibreOffice. Same status as `RASTER`.

A task whose DOCX range held a *substantive* `<w:drawing>` and which has no linked, `complete` figure row is a data error, not an acceptable state. A drawing with no image, no text box and only bare connector lines is not substantive and is not counted.

`variant_code` ∈ `100` standard, `200` autism/Asperger adaptation, `660` blind, `700` deaf. `paper_version` is A or B. `session_code` is the CKE session, for example `2605`.

**`confidence` is nullable, and null means deterministic.** Pandoc conversion has no confidence to record. Review triage must treat null as "deterministic, no review needed", never as "unknown, review everything". This distinction is what turns the spike finding into less review work rather than the same amount.

The `_660.docx` variants are the *extraction source* for their `100` counterparts, not separate content. One exercise row per logical exercise, with `sibling_docx_ref` recording where the text actually came from.

Chunk semantically, following document structure. Fixed-token chunking is a fallback for unstructured documents only, and when used it must be recorded in `extraction_method`.

Every chunk keeps its page and section. Provenance loss at ingestion time is unrecoverable later.

### Knowledge

* `concepts`: id, topic_id, name, description, explanation, difficulty, order_index, verification_status
* `formulas`: id, topic_id, name, latex_raw, latex_normalised, description, conditions, order_index, verification_status
* `methods`: id, topic_id, name, when_to_use, steps (structured), verification_status
* `examples`: id, topic_id, concept_id, statement, worked_solution, difficulty, verification_status
* `exercises`: id, topic_id, parent_exercise_id, exercise_number, statement, statement_latex_raw, statement_latex_normalised, difficulty, exercise_type, solution, solution_steps, final_answer_repr, skills_required, origin, verbatim_ok, variant_group_id, points_available, verification_status, timestamps
* `misconceptions`: id, topic_id, name, description, incorrect_reasoning, correct_reasoning, example, severity, verification_status
* `learning_objectives`: id, topic_id, statement, bloom_level, order_index
* `exercise_figures`: many-to-many between exercises and figures, since a figure can serve several subtasks

`origin` ∈ `OFFICIAL | LICENSED | OPEN | HUMAN_CREATED | AI_GENERATED`

`verification_status` ∈ `DRAFT | AI_GENERATED | PENDING_REVIEW | AUTO_VERIFIED | APPROVED | REJECTED`

**Raw and normalised LaTeX are separate fields and are not interchangeable.** `*_raw` is pandoc output, used for display. `*_normalised` is the re-parsed unambiguous form, used for verification. See section 2a for why. A row with raw LaTeX and no normalised form is valid; it simply cannot be auto-verified.

`parent_exercise_id` models the `Zadanie 12` / `Zadanie 12.1` relationship. A parent carries the shared stem and usually has no point value of its own. The stem must be attached to every child at read time, since a subtask read alone is generally incomplete.

`final_answer_repr` is a machine-checkable representation of the answer: a SymPy-parseable expression, a numeric value with tolerance, or an explicit `NOT_MACHINE_CHECKABLE` marker. See section 7.

Geometry and statistics exercises are meaningless without their diagrams. An exercise whose source region contained a figure and which has no linked figure row is a data error, not an acceptable state. Because pandoc drops `WORD_SHAPE` figures silently and they are the only kind the corpus uses for exercises, this must be caught structurally: count `<w:drawing>` elements in each task's DOCX range and record it (`ExerciseChunk.expected_figure_count` in M0), so a lost figure surfaces as `expected > linked` rather than as nothing.

### Attribution

* `knowledge_sources`: polymorphic link table joining any knowledge row to one or more `source_chunks`, with a relation type (`DERIVED_FROM`, `SUPPORTED_BY`, `CONTRADICTS`).

Every knowledge row has at least one source link or is explicitly marked `AI_GENERATED` with no source. There is no third state.

### Knowledge Specification

The Knowledge Specification for a topic is **an assembled, cached view over the normalized tables above**, not an independently authored document.

* `knowledge_specs`: id, topic_id, version, assembled_json, assembled_at, spec_hash, status

It is regenerated whenever underlying approved rows change, and its hash is recorded on anything generated from it. This prevents the spec from drifting away from the tables it summarizes.

All downstream agents read the Knowledge Specification. No downstream agent performs independent research on a topic. This is what prevents four episode types from contradicting each other.

### Episodes and scenes

* `episodes`: id, topic_id, episode_type, status, target_duration_seconds, estimated_duration_seconds, knowledge_spec_hash, plan_json, model, prompt_version, pipeline_version, timestamps
* `scenes`: id, episode_id, order_index, scene_type, objective, narration, visual_description, equations, visual_intent, estimated_duration_seconds, status

`episode_type` ∈ `THEORY | EXERCISES | COMMON_MISTAKES | CHALLENGE`

`visual_intent` is renderer-independent. It describes what must be shown and what must change, never how to draw it. "Show a parabola, highlight the vertex, translate the vertex vertically, show the equation updating in step" is correct. Anything containing Manim class names, colours, coordinates, or code is wrong and must fail validation.

---

## 6. THE RENDERER CONTRACT

This is the most important interface in the repository, because the consumer is built by a different system on a different schedule.

Produce `contracts/scene_spec/v1.schema.json`, a standalone versioned JSON Schema, generated from the Pydantic models and committed to the repo. It defines exactly what an episode's scene plan looks like when it leaves this system.

Rules:

* the schema is versioned and additive; breaking changes mean `v2`, never an edit to `v1`
* the contract contains no renderer-specific fields
* every emitted scene plan validates against the committed schema in CI
* `scripts/export_scene_spec.py` writes a sample scene plan and the schema to `contracts/`, so the rendering repo can develop against it without this repo running

Equations crossing this boundary carry the **raw** LaTeX, since the renderer displays rather than evaluates them.

Also produce `contracts/README.md` explaining the contract in prose for whoever is building the renderer.

---

## 7. MATHEMATICAL VERIFICATION

Verification is real but partial. Do not build a trust model that assumes everything can be checked.

### Normalisation comes first

**Nothing reaches SymPy unnormalised.** Pandoc's LaTeX is visually faithful and semantically ambiguous; see section 2a for the worked example. The normalisation layer is a real component, not a helper function.

```text
pandoc LaTeX (raw, for display)
→ normalise and re-parse
→ unambiguous expression (for verification)
→ or NOT_MACHINE_CHECKABLE
```

An expression that does not normalise unambiguously is marked `NOT_MACHINE_CHECKABLE` and routed to human review. It is never guessed at, and a plausible-looking parse is not evidence of a correct one.

### Verification

```text
Generate or extract
→ produce final_answer_repr independently of the generating call
→ solve with SymPy
→ compare
→ AUTO_VERIFIED or PENDING_REVIEW
```

Requirements:

* the verifying call must not be the same call that generated the content
* numeric answers compare with explicit tolerance
* symbolic answers compare via `simplify(a - b) == 0`, not string equality
* the verifier runs in a sandboxed subprocess with a timeout, since parsed expressions are effectively untrusted input
* anything not machine-checkable (geometry constructions, proofs, word problems with modelling steps, conceptual explanations) is marked `NOT_MACHINE_CHECKABLE` and routed to human review

Expect a substantial fraction of the corpus to land in human review. That is an expected outcome and not a bug. Track the auto-verification rate per topic as a dashboard metric, because it shows where the pipeline is actually weak.

Where an exercise comes from a paper with a `zasady oceniania`, the marking scheme's point breakdown is an independent check on both the answer and the number of solution steps. Use it.

---

## 8. DEDUPLICATION AND MERGE

Multiple sources will describe the same formula, the same misconception, and near-identical exercises. The schema must not accumulate five copies of the delta formula.

Build a merge step in the extraction pipeline:

* candidate detection by normalized name, then by normalised LaTeX for formulas, then by embedding similarity for prose
* merges preserve all source links from all merged rows
* merges are recorded in a `merge_events` table and are reversible
* an automatic merge above a high confidence threshold is allowed; anything below becomes a review task
* **never merge across a `variant_group_id`.** Parallel A and B papers contain structurally similar exercises with different values. They are distinct exercises.

Compare on `latex_normalised`, never on `latex_raw`. Raw forms differ by invisible grouping artifacts that have nothing to do with whether two formulas are the same.

Never delete a source link during a merge. Provenance accumulates.

---

## 9. HUMAN REVIEW IS THE BOTTLENECK

Review throughput, not generation throughput, limits this system. Treat review tooling as a primary feature and build it in M3, not at the end.

Requirements:

* a single review queue with typed items (formula, exercise, misconception, curriculum mapping, merge candidate, extraction conflict, normalisation failure)
* items sorted by risk and confidence, so the reviewer sees the doubtful things first
* **deterministically extracted content (null confidence) does not enter the queue by default.** It is already trustworthy at the extraction step. Only its downstream classification and knowledge extraction need review.
* keyboard-driven approve, reject, edit; one item per screen; no page reloads between items
* batch approval for items sharing high confidence and the same topic and source
* every decision records reviewer, timestamp, and prior status
* rejections require a reason code, because rejection reasons are the training signal for improving prompts

The dashboard's home page is the review queue with its depth and per-type breakdown. Everything else is secondary.

---

## 10. CURRICULUM MAPPING

After ingestion, map source chunks to the curriculum: subject, unit, topic, concept, difficulty, content type.

Mapping is AI-assisted and always records `confidence` and `mapping_status` ∈ `AI_SUGGESTED | REVIEW_REQUIRED | APPROVED | REJECTED`.

**A chunk maps to one PRIMARY requirement and zero or more secondaries.** The M3 calibration pass found ~1/3 of exam tasks genuinely test two or more requirements (`m3/mapping_multitopic_scan.md`); forcing one is why the agent's mid-range confidence was uninformative. `chunk_mappings` holds one `is_primary` row per chunk plus secondary rows; a reviewer promotes a secondary with one keystroke. `exercises.topic_id` tracks the primary; secondaries reach exercises via `exercise_topics` in M4. Coverage is reported two ways — requirements a chunk *primarily drills* vs *also touches* — and the EXERCISES format's count is the first.

Note that mapping confidence is separate from extraction confidence. A chunk can be deterministically extracted and still be uncertainly mapped.

An unmapped chunk is a normal state and must be visible in the dashboard as a count. Silently dropping unmappable material is not acceptable, because unmapped volume is the signal that the curriculum tree is incomplete.

---

## 11. KNOWLEDGE EXTRACTION

For each topic, aggregate its approved mapped chunks and extract: definitions, concepts, formulas, methods, examples, exercise types, misconceptions, prerequisites, learning objectives, difficulty progression, Matura relevance.

Hard rules for the extraction agent:

* it may not invent facts absent from the provided chunks
* every extracted item carries source chunk references
* when sources disagree, it emits both readings plus a `CONFLICT` flag; it does not pick a winner
* when information is missing, it emits a gap record rather than filling the gap

Conflicts and gaps become review queue items. This is the point where quality is won or lost.

---

## 12. AGENTS

Five agents, each with a narrow contract, strict Pydantic input and output schemas, and access only to the data it needs:

1. **Ingestion Agent**: unstructured documents → structured chunks with content types. **Not used for Track A**, which is deterministic and needs no model.
2. **Mapping Agent**: chunk → curriculum location with confidence
3. **Knowledge Agent**: topic chunks → structured knowledge items with source references
4. **Exercise Agent**: topic knowledge spec → exercises with independent answer representations
5. **Planner Agent**: knowledge spec plus episode type → episode plan and scene plan

Do not add agents beyond these until the five work. Extraction from DOCX is code, not an agent. Normalisation is code, not an agent. Verification is code, not an agent. QA is code, not an agent.

Every agent call follows:

```text
LLM
→ structured response
→ Pydantic validation
→ business rule validation
→ database
```

Never `LLM → database`. Raw model JSON is never trusted.

Put domain constraints in validators rather than in prompts. Point values in range, exercise numbers monotonically increasing within a paper, subtask counts matching the marking scheme. Prompts are suggestions; validators are guarantees, and the difference shows up at a thousand pages. Feed validation error text back into retry prompts, since that is what makes a retry converge rather than repeat.

---

## 13. EPISODE PLANNING

Every topic yields four episode types, following the arc `UNDERSTAND → PRACTICE → AVOID MISTAKES → TEST YOURSELF`.

The planner receives topic, episode type, difficulty, knowledge spec, approved examples, approved exercises, approved misconceptions, prerequisites, Matura relevance, and target duration. It produces an episode plan, then a scene plan. The scene plan always exists as an intermediate representation; nothing downstream ever receives an unstructured wall of script.

### Structures

**THEORY**, target 9 to 12 minutes: Hook (concrete problem, never generic filler) → Intuition → Formal Definition → Why It Works → 2 to 3 progressively harder guided examples → Matura Connection → Summary as a compact mental model.

**EXERCISES**, target 10 to 16 minutes: Quick Recall → Basic → Standard → Different Form → Multi-Step → Matura Challenge → Solution Pattern. Every exercise follows: present, thinking pause, identify given information, choose strategy, solve step by step, verify, final answer, key insight.

The seven harvested Track A papers supply five or more exercises for only ~22 of 73 podstawowy requirements (settled decision 10; `m2/exercise_coverage.md`). For most topics the exercises an EXERCISES episode uses will be **generated by the Exercise Agent and symbolically verified**, not harvested. Harvested items, where they exist, anchor the difficulty ladder and the Matura-authentic phrasing; the generator fills the rest. This is the expected steady state, not a shortfall to apologise for — a topic with no harvested exercises is still a valid EXERCISES episode once the generator has produced and verification has passed the required count.

**COMMON_MISTAKES**, target 8 to 12 minutes: Hook showing a convincing wrong solution → five mistakes → anti-mistake checklist. Each mistake covers the problem, the incorrect reasoning, the exact error, why it is tempting, the correct reasoning, and how to avoid it. Mistakes come from the approved `misconceptions` table. The planner may not invent mistakes to fill time; if a topic has fewer than five approved misconceptions, the episode is blocked with `INSUFFICIENT_KNOWLEDGE` and a review task is created.

**CHALLENGE**, target 8 to 15 minutes: Rules → five problems of increasing difficulty → score and diagnosis. Internal scoring is never presented as official Matura scoring.

### Duration

The planner estimates duration from narration length, pause budgets, thinking-time budgets, and per-scene visual complexity, using a documented model in `planning/duration_model.py`.

If an episode plan estimates under 8 minutes, it is not marked ready. It goes back to the planner with instructions to add educational substance. Padding narration is a failure, not a fix.

Note in the code that this is an estimate and that the renderer, once it exists, will produce the authoritative figure. Do not attempt to be precise here.

---

## 14. QUALITY CONTROL

Automated checks run before an episode plan is marked ready for the renderer.

**Content**: correct topic and episode type, prerequisites respected (nothing used that a prior topic has not introduced), no unsupported Matura claims, no contradiction with the knowledge spec, sufficient approved material to fill the structure.

**Mathematics**: every referenced formula APPROVED, every referenced exercise APPROVED or AUTO_VERIFIED, every equation parses as valid LaTeX.

**Structure**: all required scene types present in order, no empty narration, no empty visual intent, estimated duration at or above 8 minutes, scene plan validates against the committed Scene Spec schema, no renderer-specific leakage in `visual_intent`.

**Assets**: every exercise requiring a figure has one linked, and every linked figure has `render_status` complete.

QA failures block the episode and create a review item. No unverified content reaches a ready state silently.

---

## 15. JOBS, VERSIONING, ERRORS

Job types for this scope only:

```text
INGEST_DOCUMENT
CONVERT_DOCX
EXTRACT_MEDIA
RENDER_VECTOR_FIGURE
SEGMENT_EXERCISES
NORMALISE_LATEX
EXTRACT_PDF_TEXT
CHUNK_DOCUMENT
CLASSIFY_CHUNK
MAP_CHUNK
EXTRACT_KNOWLEDGE
MERGE_CANDIDATES
VERIFY_FORMULA
GENERATE_EXERCISE
VERIFY_EXERCISE
ASSEMBLE_KNOWLEDGE_SPEC
GENERATE_EPISODE_PLAN
GENERATE_SCENE_PLAN
RUN_QA
```

Every job row records status, attempts, input, output, error, timestamps, model, prompt version, and pipeline version. Failed jobs are retryable individually. Retries are granular: a failed scene plan does not invalidate the episode plan, and a failed chunk does not invalidate the document.

Prompts live in versioned files, not inline strings. Changing a prompt increments its version. It must always be possible to determine exactly how any row was produced.

### Migration hygiene

* one linear revision chain, one revision per logical feature
* meaningful revision slugs, not hashes
* revisions are immutable once applied to any shared database
* **no pgvector index in any migration, ever.** An IVFFlat index built against an empty table has its quality fixed at build time by k-means over nothing, and degrades recall silently and permanently. If vector search is ever needed, use HNSW and build it in a post-load script.

### Failure modes

* knowledge extraction fails → topic marked `KNOWLEDGE_EXTRACTION_FAILED`, no episodes generated
* normalisation fails → expression marked `NOT_MACHINE_CHECKABLE`, routed to review, never guessed
* exercise verification fails → exercise unusable, not silently included
* figure render fails → exercise blocked if the figure is required
* scene plan fails → retry that scene, not the episode
* QA fails → episode blocked

---

## 16. DASHBOARD

Read-mostly, minimal, functional over pretty.

* **Review queue** (home): depth by type, risk-sorted, keyboard-driven
* **Curriculum tree**: units and topics with per-topic knowledge completeness indicators
* **Topic page**: knowledge spec, sources, prerequisites, concepts, formulas, exercises, misconceptions, episodes
* **Source page**: documents, extraction status, chunk counts, unmapped chunk count
* **Production board**: `PLANNED | EXTRACTING | KNOWLEDGE_READY | PLANNING | SCENES_READY | QA_FAILED | READY_FOR_RENDER`
* **Episode page**: plan, scenes, QA results, versions, the exported scene plan JSON with a download button
* **Pipeline health**: job failures, auto-verification rate by topic, normalisation failure rate, unmapped volume, review queue growth rate

`READY_FOR_RENDER` is the terminal state in this repository.

---

## 17. BUILD ORDER

Work through these in order. **Stop at the end of each milestone, summarize what exists, and wait for my confirmation before continuing.** Do not run ahead.

---

### M0. Extraction pipeline foundations

The spike in section 2a already answered the question this milestone originally existed to ask. The corpus splits:

**Track A, structured.** Any CKE document with a `_660.docx` sibling. Deterministic pandoc conversion, no model, no confidence score. Expected to cover the informatory, exam papers, and marking schemes, which is most of what M1 through M5 need.

**Track B, unstructured.** The podstawa programowa and any textbooks that arrive later. Deferred.

Build Track A.

#### M0.1 Corpus split table

For every document in `sources/MANIFEST.md`, establish whether a `_660.docx` sibling exists. The convention is systematic: variant code `100` becomes `660`, extension becomes `.docx`.

Produce a table: document, has DOCX sibling, oMath count, drawing count, media count, track.

Check whether marking schemes (`-zasady`) have DOCX siblings too. They are the validation oracle and a `solution_steps` source, so a structured version is worth having.

#### M0.2 The pandoc pipeline

Use pandoc. Do not build a custom OMML converter. Record this in an ADR with the evidence from section 2a.

Always pass `--extract-media`. Without it pandoc emits `\includegraphics{media/imageN.jpeg}` referring to files it never writes, silently producing broken asset references.

Build a thin wrapper that:

1. converts DOCX to LaTeX with media extracted to a per-document directory
2. strips cover boilerplate (the security notice image, the invigilator answer grid rendered as a wide `longtable`) before parsing
3. segments on `Zadanie N.` and `Zadanie N.M`, capturing `points_available` from the `(0--M)` marker
4. writes chunks with `extraction_method = 'pandoc_omml'` and `confidence = NULL`

Segmentation pattern, confirmed against a real paper:

```
Zadanie 7. (0--2)          → exercise, 2 points
Zadanie 12.                → parent, no points, holds shared stem
Zadanie 12.1. (0--2)       → subtask
```

A parent with no point marker carries the shared stem for its subtasks, and that stem must attach to every child, since a subtask read alone is usually incomplete.

**Validation gate.** Cross-check the extracted exercise list against the paper's own `zasady oceniania`, which independently enumerates every task with its point values. Counts and point values must match exactly. This is a hard gate, not a report line.

#### M0.3 LaTeX normalisation study

Characterise the problem described in section 2a. Do not solve it yet; the normalisation layer itself is M5 work, but M5 cannot be scoped without this number.

Sample 30 equations spanning fractions, radicals, logs, powers, systems and piecewise definitions. For each, record whether the pandoc LaTeX parses to the intended expression. Report the failure rate and the failure patterns.

Store both forms from the start: raw for display, normalised (or null) for verification.

#### M0.4 Figures

Three routes, all present in the corpus:

* **Raster** (`image1.jpeg`, `image5.png`): extracted directly by `--extract-media`. Attach to the exercise containing the reference.
* **Vector WMF** (`image2.wmf`): a Windows Metafile, not usable as-is. Establish a conversion route, most likely LibreOffice headless or `libwmf`, and verify output quality on a real geometry diagram.
* **Word-drawn shapes** (the informator's 25 drawings with zero media entries): not files at all. These need a render pass, probably DOCX to PDF via LibreOffice followed by region cropping.

Geometry and statistics exercises are unusable without their figures, so this is not optional. Report which route works for each format and what fails.

#### M0.5 Track B: minimal audit only

Two questions, then stop.

**1. Text layer and diacritics on the PDF-only sources.**

```bash
for f in sources/raw/*.pdf; do
  chars=$(pdftotext "$f" - 2>/dev/null | tr -d '[:space:]' | wc -c)
  pages=$(pdfinfo "$f" | awk '/^Pages:/{print $2}')
  echo "$f pages=$pages chars_per_page=$((chars / (pages>0?pages:1)))"
done
```

Under roughly 100 characters per page means image-only.

Assert on Polish diacritics: the ratio of `ą ć ę ł ń ó ś ź ż` to total letters runs roughly 8 to 12 percent in Polish prose. A near-zero ratio means silent encoding corruption from a missing `ToUnicode` CMap, not a document without diacritics. Use `ł` as the canary. This failure raises no exception, so assert on it explicitly.

**2. Nothing else.** Do not run an extractor comparison. It is work for whenever textbooks arrive, and the landscape will have moved. Record the deferral in an ADR, pointing at the survey in `docs/sources.md` as the starting point.

#### M0.6 Curriculum tree

The informator links to a mathematics-only extract of the podstawa programowa:

```
https://cke.gov.pl/images/_EGZAMIN_MATURALNY_OD_2015/Formula_2023/podstawa_programowa/matematyka.pdf
```

Check this first. A maths-only document is a far better source than the full Dz.U. regulation, which covers every subject.

**Verify it reflects the 2024 amendment** before using it. The URL sits under a `_OD_2015` path, which is suspicious. Cross-check several requirement numbers against Dz.U. 2024 poz. 1019. If they diverge, the Dz.U. text wins and this shortcut is discarded.

Either way, **this is a one-off, hand-verified job, not a pipeline.** The tree is on the order of 100 nodes. Extract semi-manually, present it for node-by-node verification, and commit the result as a checked-in seed file. Every episode this system ever produces rests on this tree being correct.

Preserve official numbering as `official_requirement_code`. Cover both levels, noting that rozszerzony is podstawowy plus additions rather than a separate tree.

#### M0 deliverable

1. the corpus split table
2. a working pandoc wrapper with media extraction, boilerplate stripping, and `Zadanie` segmentation
3. one exam paper segmented and cross-validated against its marking scheme, counts and points matching exactly
4. the 30-equation normalisation study with its failure rate and patterns
5. figure extraction working for raster, WMF, and Word shapes, with any failures named
6. the text-layer and diacritic audit for PDF-only sources
7. the hand-verified curriculum seed file
8. ADRs for: pandoc chosen over custom conversion, figure routes per format, Track B deferral

Stop and wait.

---

### M1. Foundation

Repo structure, Docker Compose with Postgres, Alembic wired, config and secrets, curriculum tables, seeding from the hand-verified M0.6 file, `sources` seeded from `sources/MANIFEST.md`.

Seeding is idempotent and re-runnable. Do not have a model generate or infer licensing metadata; it comes from the manifest, which is authored by hand.

Tests: curriculum hierarchy, prerequisite cycle detection against a deliberately introduced loop, seed idempotency. Stop.

---

### M2. Ingestion

Source documents, the Track A pipeline productionised from the M0 wrapper, semantic chunking, figure extraction, provenance preservation, job system with a worker, synthetic fixture corpus, tests.

Figure extraction is the `WORD_SHAPE` route productionised from the M0.4 scaffold (`figures_render.py`): DOCX→PDF via LibreOffice, then crop each task's figure region, cleaning up the failure modes named in `docs/decisions/0004-figure-routes.md`. Re-verified across all seven Track A papers: every exercise figure is `WORD_SHAPE` (SPEC §2a finding 4). The `RASTER` and `WMF` handlers stay wired to `source_format` for a future source but no exercise here uses them. Do not build three parallel pipelines. Attribution ignores a `<w:drawing>` with no substance (no image, no text, bare connectors only).

Gate: one real arkusz ingests end to end with exercise numbers, point values, parent/subtask relationships, and figures intact (every `expected_figure_count > 0` task has a linked, rendered figure), and its exercise count matches its marking scheme exactly. Stop.

---

### M3. Mapping and review

Mapping agent with confidence, review queue backend, review UI, dashboard skeleton with curriculum tree and source pages.

Gate: I can approve and reject mappings by keyboard without touching the mouse, and deterministically extracted chunks do not clutter the queue. Stop.

As built (ADR 0009): `chunk_mappings` / `review_items` / `review_decisions` (migrations `0004`–`0007`). The Mapping Agent is a Protocol with `ClaudeMappingAgent` (`claude-opus-5`) and an offline `StubMappingAgent`, chosen by `ANTHROPIC_API_KEY` presence, so the whole path runs without the network. A chunk gets one **primary** `chunk_mappings` row (`is_primary`, unique per chunk) plus **secondary** rows for the other requirements it tests (section 10); a subtask fragment is sent to the agent with its parent's shared stem (`MappingRequest.stem`, prompt `m3-map-v2`). `AUTO_APPROVE_THRESHOLD = 0.70` on the **primary's** mapping confidence is the queue-entry lever, set from the 28 Aug 2026 calibration curve (seven papers, top-level + subtask, `m3-map-v2`, 82 reviewed decisions, 56 at/above 0.70 all accepted — ADR 0009 §1b). Re-calibrate with `zaspro.mapping.run <arkusz> --remap --review-all` then `zaspro.review.calibration_run` (`GET /review/calibration`, dashboard `/calibration`); `review_items.input_defect` excludes decisions made on broken agent input. At or above the threshold a mapping is `AI_SUGGESTED` and not queued *except* a permanent 3% audit sample (`review_items.audit_sample`, deterministic per chunk+prompt), so the system can never auto-approve a block wholly unseen. Below it: `REVIEW_REQUIRED` with one `ReviewItem` (on the primary). Only `AI_SUGGESTED` or human-`APPROVED` primaries propagate to `exercises.topic_id`. `zaspro.review.queue` does next-by-risk, `record_decision` (immutable, records prior status + frozen mapping confidence, REJECT needs a reason code, `PROMOTE` swaps a secondary into the primary slot in one keystroke), and `batch_approve`. API: `zaspro.api` (FastAPI). Dashboard: `dashboard/` (Next.js App Router) — review page is one client component, keys `a`/`p`/`r`+digit/`e`+`j`/`k`/`b`/`s`, secondaries shown on the card, no route change between items.

---

### M4. Knowledge

Knowledge agent, concepts, formulas, methods, examples, objectives, misconceptions, source attribution, conflict and gap flagging, dedupe and merge, knowledge spec assembly and hashing. Stop.

Three constraints from the start (see ADR for M4):

* **`exercise_topics` is built before the knowledge agent runs.** A topic's chunks for aggregation are those where it is the **primary or an approved secondary** mapping (section 10). Extracting from primaries only rebuilds the narrow view that multi-topic mapping was meant to remove.
* **Read the stem-inclusive text.** Exercise text comes from `Exercise.full_statement` (stem + body), never `SourceChunk.text` alone — the M3 stem defect was exactly this shape.
* **One requirement ≠ one episode.** `official_requirement_code` is the legal definition of what is examinable, not a teaching unit. Episode generation will sit on a **teaching layer** above the requirements (grouping via `topics.parent_id`, requirements as `parent_id` children keeping their code), built as work **between M4 and M6**. M4 must not assume a 1:1 requirement→episode mapping anywhere.

---

### M5. Exercises and verification

The LaTeX normalisation layer, scoped from the M0.3 findings. Exercise extraction and generation, SymPy verification in a sandboxed subprocess, answer representations, marking-scheme cross-checks, auto-verification and normalisation-failure rate metrics. Stop.

---

### M6. Episode and scene planning

Planner agent, four episode structures, duration model, scene plans, Scene Spec v1 schema exported to `contracts/`, QA checks, episode pages in the dashboard. Stop.

---

### M7. Full-path validation

One topic taken from raw source to a QA-passing scene plan for all four episode types, using the synthetic corpus plus one real arkusz.

Produce a preprocessing report: documents, pages, chunks, topics, concepts, formulas, exercises, misconceptions, figures, source references, unmapped material, ambiguous material, conflicts, normalisation failures, and items requiring review.

Only after M7 do we discuss mass processing of textbooks.

---

## 18. TESTING

Automated tests for: curriculum hierarchy and prerequisite cycles, seed idempotency, source reference integrity, chunk provenance survival, Polish diacritic assertion against a deliberately corrupted fixture, `Zadanie` segmentation including the parent/subtask case, marking-scheme cross-validation, LaTeX normalisation including the `\log_{8}{4 - \log_{8}32}` case as a regression test, extraction schema conformance, mapping status transitions, merge reversibility including the variant-group exclusion, exercise verification including deliberately wrong answers that must be caught, knowledge spec assembly and hash stability, episode and scene generation, duration estimation, QA rules, job retry semantics, and Scene Spec schema conformance.

Build a small synthetic curriculum fixture with three topics and fake source documents. Tests must run without network access and without real source material. AI calls are mocked in tests; a separate, small, manually-run suite covers live model behaviour.

---

## 19. WORKING AGREEMENT

* Document every non-obvious architectural decision as a short ADR in `docs/decisions/`, including the alternative rejected and why.
* Strong typing everywhere. Pydantic at every boundary. No untyped dicts crossing module lines.
* Ask before adding a dependency that brings infrastructure with it.
* If something in this document turns out to be wrong on contact with reality, say so and propose the change rather than quietly working around it.
* Prefer the smallest implementation that lets the next milestone start. This system will be refined iteratively, not designed perfectly on the first pass.
* Files under `sources/raw/` are read-only source material. Do not process them beyond what the current milestone requires.

Start with M0.