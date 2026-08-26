# ZasPro: Polish Matura Knowledge Base and Episode Planning System

Authoritative specification. Version 2, 26 August 2026.

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

These follow from a source-and-tooling research pass completed 26 August 2026. They are decided. Do not reopen one without telling me why.

1. **The curriculum ground truth is the 2024 podstawa programowa** (Dz.U. 2024 poz. 1019), not the `wymagania egzaminacyjne`. The latter applied only to the 2023 and 2024 exams and is superseded. Many secondary sources still cite it. Do not seed from a secondary source or from model recollection.
2. **Formuła 2023 only.** Formuła 2015 material is recorded in the source manifest but not ingested. Revisit only if exercise volume becomes a constraint.
3. **Verbatim source text is stored**, with `verbatim_ok = false` by default. Publishable derivatives are separate rows carrying their own provenance. Storage and publication are distinct concerns and the schema must keep them distinct.
4. **Parallel paper versions (A/B) are separate exercise rows**, joined by `variant_group_id`. Deduplication must never merge across a variant group.
5. **The `zasady oceniania` marking scheme is both a validation oracle and a knowledge source.** It independently enumerates every exercise with point values, and its partial-credit breakdown maps onto `solution_steps`.
6. **Exercise boundary recovery outranks formula fidelity.** An exercise with a slightly imperfect equation is repairable. An exercise whose boundaries dissolved into the next one is not.

The verified source inventory and extraction tooling research live in `docs/sources.md`. Read it before M0.

---

## 3. STACK

* **Python 3.12** owns the schema, migrations, ingestion, extraction, verification, and job execution. PDF parsing and symbolic maths are Python-native and this is not negotiable.
* **PostgreSQL 16** as the single source of truth. `pgvector` is added only when a retrieval task actually needs it, not in the first migration.
* **Alembic** for migrations. One migration system only.
* **SQLAlchemy 2.x** typed ORM models, modern declarative style with `Mapped[]` annotations and a `type_annotation_map` for reused domain types.
* **Pydantic v2** for all AI input and output schemas and all ingestion contracts.
* **FastAPI** for the internal API.
* **A job runner**: start with a Postgres-backed queue table plus a worker loop. Do not add Celery, Redis, or RabbitMQ until the simple version is provably insufficient.
* **Next.js (App Router) dashboard**, read-mostly, calling the FastAPI backend. The dashboard does not own or migrate the schema and does not talk to Postgres directly.
* **Local filesystem** for source documents and rendered page images in development, behind a storage interface with an S3-compatible implementation available. Only source documents, page images, and extracted figures are stored, nothing else.

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
* `topics`: id, unit_id, name, slug, description, level, order_index, official_requirement_code, status, timestamps
* `topic_prerequisites`: topic_id, prerequisite_topic_id, importance, reason

`official_requirement_code` is the link back to the podstawa programowa numbering and is unique where present.

**Representation.** Adjacency list with a `parent_id` self-foreign-key. The tree is small, shallow and effectively read-only after seeding, so the performance arguments for materialized paths and `ltree` do not apply. Adjacency is the only representation where reparenting is a single-row update that cannot leave the tree inconsistent. Add a generated materialized path column later if the same recursive CTE gets written repeatedly. Consider `ltree` only if its pattern-matching operators are wanted, which is a different motivation from performance.

**Prerequisites** are a separate structure: a DAG over topics and concepts, not a tree over curriculum sections. Do not conflate them. Enforce acyclicity at write time using PostgreSQL's `CYCLE` clause (`CYCLE id SET is_cycle USING cycle_path`, available since PG 14) rather than trusting the seeding process. Prerequisite edges are the rows most likely to be added by hand or inferred by a model, and therefore the rows most likely to introduce a loop.

### Sources and provenance

* `sources`: id, title, author, publisher, year, source_type, licence_status, verbatim_ok, reuse_notes, url, file_ref, notes, processing_status
* `source_documents`: id, source_id, file_ref, page_count, extraction_status, variant_code, paper_version, session_code, sibling_docx_ref
* `source_chunks`: id, source_document_id, page, chapter, section, heading, content_type, text, latex, order_index, extraction_method, confidence
* `figures`: id, source_document_id, page, bbox, image_ref, caption

`source_type` ∈ `PODSTAWA_PROGRAMOWA | OFFICIAL_CKE | EXAM | MARKING_SCHEME | FORMULA_SHEET | TEXTBOOK | OPEN_EDUCATIONAL_RESOURCE | USER_PROVIDED | OTHER`

`content_type` ∈ `EXPLANATION | DEFINITION | FORMULA | EXAMPLE | EXERCISE | SOLUTION | THEOREM | NOTE | WARNING`

`variant_code` ∈ `100` standard, `200` autism/Asperger adaptation, `660` blind, `700` deaf. `paper_version` is A or B. `session_code` is the CKE session, for example `2605`.

Do not ingest the 200, 660 and 700 adaptation variants as separate exercises. They are content-equivalent to the standard version. Record their existence on the document row so the DOCX siblings remain reachable.

Chunk semantically, following document structure (chapter → section → subsection → concept → example → exercise). Fixed-token chunking is a fallback for unstructured documents only, and when used it must be recorded in `extraction_method`.

Every chunk keeps its page and section. Provenance loss at ingestion time is unrecoverable later.

### Knowledge

* `concepts`: id, topic_id, name, description, explanation, difficulty, order_index, verification_status
* `formulas`: id, topic_id, name, latex, description, conditions, order_index, verification_status
* `methods`: id, topic_id, name, when_to_use, steps (structured), verification_status
* `examples`: id, topic_id, concept_id, statement, worked_solution, difficulty, verification_status
* `exercises`: id, topic_id, statement, statement_latex, difficulty, exercise_type, solution, solution_steps, final_answer_repr, skills_required, origin, verbatim_ok, variant_group_id, points_available, verification_status, timestamps
* `misconceptions`: id, topic_id, name, description, incorrect_reasoning, correct_reasoning, example, severity, verification_status
* `learning_objectives`: id, topic_id, statement, bloom_level, order_index
* `exercise_figures`: many-to-many between exercises and figures, since a figure can serve several subtasks

`origin` ∈ `OFFICIAL | LICENSED | OPEN | HUMAN_CREATED | AI_GENERATED`

`verification_status` ∈ `DRAFT | AI_GENERATED | PENDING_REVIEW | AUTO_VERIFIED | APPROVED | REJECTED`

`final_answer_repr` is a machine-checkable representation of the answer: a SymPy-parseable expression, a numeric value with tolerance, or an explicit `NOT_MACHINE_CHECKABLE` marker. See section 7.

Geometry and statistics exercises are meaningless without their diagrams. An exercise whose source region contained a figure and which has no linked figure row is a data error, not an acceptable state.

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

Also produce `contracts/README.md` explaining the contract in prose for whoever is building the renderer.

---

## 7. MATHEMATICAL VERIFICATION

Verification is real but partial. Do not build a trust model that assumes everything can be checked.

Pipeline for any exercise or worked example:

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

Expect roughly half of the corpus to land in human review. That is an expected outcome and not a bug. Track the auto-verification rate per topic as a dashboard metric, because it shows where the pipeline is actually weak.

Where an exercise comes from a paper with a `zasady oceniania`, the marking scheme's point breakdown is an independent check on both the answer and the number of solution steps. Use it.

---

## 8. DEDUPLICATION AND MERGE

Multiple sources will describe the same formula, the same misconception, and near-identical exercises. The schema must not accumulate five copies of the delta formula.

Build a merge step in the extraction pipeline:

* candidate detection by normalized name, then by LaTeX normalization for formulas, then by embedding similarity for prose
* merges preserve all source links from all merged rows
* merges are recorded in a `merge_events` table and are reversible
* an automatic merge above a high confidence threshold is allowed; anything below becomes a review task
* **never merge across a `variant_group_id`.** Parallel A and B papers contain structurally similar exercises with different values. They are distinct exercises.

Never delete a source link during a merge. Provenance accumulates.

---

## 9. HUMAN REVIEW IS THE BOTTLENECK

Review throughput, not generation throughput, limits this system. Treat review tooling as a primary feature and build it in M3, not at the end.

Requirements:

* a single review queue with typed items (formula, exercise, misconception, curriculum mapping, merge candidate, extraction conflict)
* items sorted by risk and confidence, so the reviewer sees the doubtful things first
* keyboard-driven approve, reject, edit; one item per screen; no page reloads between items
* batch approval for items sharing high confidence and the same topic and source
* every decision records reviewer, timestamp, and prior status
* rejections require a reason code, because rejection reasons are the training signal for improving prompts

The dashboard's home page is the review queue with its depth and per-type breakdown. Everything else is secondary.

---

## 10. CURRICULUM MAPPING

After ingestion, map source chunks to the curriculum: subject, unit, topic, concept, difficulty, content type.

Mapping is AI-assisted and always records `confidence` and `mapping_status` ∈ `AI_SUGGESTED | REVIEW_REQUIRED | APPROVED | REJECTED`.

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

1. **Ingestion Agent**: page images and text → structured chunks with content types
2. **Mapping Agent**: chunk → curriculum location with confidence
3. **Knowledge Agent**: topic chunks → structured knowledge items with source references
4. **Exercise Agent**: topic knowledge spec → exercises with independent answer representations
5. **Planner Agent**: knowledge spec plus episode type → episode plan and scene plan

Do not add agents beyond these until the five work. Verification is code, not an agent. QA is code, not an agent.

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

**Assets**: every exercise requiring a figure has one linked.

QA failures block the episode and create a review item. No unverified content reaches a ready state silently.

---

## 15. JOBS, VERSIONING, ERRORS

Job types for this scope only:

```text
INGEST_DOCUMENT
EXTRACT_PAGES
CHUNK_DOCUMENT
CLASSIFY_CHUNK
EXTRACT_FIGURES
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
* exercise verification fails → exercise unusable, not silently included
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
* **Pipeline health**: job failures, auto-verification rate by topic, unmapped volume, review queue growth rate

`READY_FOR_RENDER` is the terminal state in this repository.

---

## 17. BUILD ORDER

Work through these in order. **Stop at the end of each milestone, summarize what exists, and wait for my confirmation before continuing.** Do not run ahead.

### M0. Extraction spike

#### M0.0 The DOCX question, before anything else

CKE publishes accessibility versions of the informatory and of every exam paper as native Word files, suffixed `_660.docx`. If these carry mathematics as OMML, the transform to LaTeX is deterministic and no extraction model is needed for that portion of the corpus.

I will have run the basic check before you start and will give you the numbers. Your job is to go deeper:

1. Convert a sample of OMML to LaTeX and check fidelity by rendering, not by string comparison.
2. Check whether exercise numbering survives as Word list structure or heading styles.
3. Check whether figures survive as embedded images with usable positioning.
4. Establish which documents in the corpus have DOCX siblings and which do not.

If OMML is present, M0 becomes "DOCX-first with a PDF fallback for sources with no DOCX sibling", and the comparison below narrows accordingly. Report before continuing.

#### M0.1 Corpus audit

```bash
for f in sources/raw/*.pdf; do
  chars=$(pdftotext "$f" - 2>/dev/null | tr -d '[:space:]' | wc -c)
  pages=$(pdfinfo "$f" | awk '/^Pages:/{print $2}')
  echo "$f pages=$pages chars_per_page=$((chars / (pages>0?pages:1)))"
done
```

Under roughly 100 characters per page means image-only.

Add a Polish diacritic assertion to the same pass. Extract text and compute the ratio of `ą ć ę ł ń ó ś ź ż` to total letters. Polish prose runs roughly 8 to 12 percent. A near-zero ratio means silent encoding corruption from a missing or wrong `ToUnicode` CMap, not a document without diacritics. Use `ł` (U+0142) as the primary canary since it has no unaccented visual fallback.

This failure is silent by nature. Nothing raises an exception. Assert on it explicitly or it surfaces in month three.

#### M0.2 Fixed rendering parameters

Fix these before any comparison and record them in the spike README:

* page raster DPI and maximum pixel dimension on the longest edge
* whether anchor text from the text layer is supplied alongside the image
* colour or greyscale

Varying these between extractors means comparing preprocessing pipelines rather than extractors. Normalise first, compare second.

#### M0.3 The comparison

Fixed sample: 20 pages spanning one arkusz PP and pages from the informator containing worked examples. Same pages for every method.

Methods, narrowed by the M0.0 result:

1. text layer alone (PyMuPDF or pdfplumber)
2. geometric rules over pdfplumber character boxes, for structure only
3. one open document parser, chosen and justified from the survey in `docs/sources.md`
4. one commercial maths OCR service on the same pages
5. page image plus vision model with a schema-constrained JSON response

#### M0.4 Success metric

Three numbers per method. The first is the gate.

1. **Exercise boundary recovery**, validated against the paper's own `zasady oceniania`, which independently lists every exercise and its point value. Target 95 percent or above. This cross-validation is automatic and free; make it a hard gate.
2. **Formula fidelity**, judged by rendering both the extracted LaTeX and the reference and comparing visually. Not by edit distance. Textually dissimilar LaTeX frequently renders identically.
3. **Cost and latency per page.** The whole Formuła 2023 maths corpus is roughly 1,200 pages, so commercial per-page pricing is a rounding error at this scale. Do not reject a method on cost grounds without doing that arithmetic.

Also record per method: Polish diacritic integrity, whether figure regions were detected with usable bounding boxes, and whether reading order survived.

#### M0.5 Curriculum annex extraction

The maths annex of Dz.U. 2024 poz. 1019 must be extracted into a clean tree.

Before parsing the ISAP PDF, check whether a Word or HTML edition exists on `zpe.gov.pl` or `gov.pl`. A structured source would make this trivial.

Either way, **this is a one-off, hand-verified job, not a pipeline.** The tree is on the order of 100 nodes. Extract semi-manually, present it to me for node-by-node verification, and commit the result as a checked-in seed file. Every episode this system ever produces rests on this tree being correct.

Preserve the official numbering as `official_requirement_code`. Cover both `poziom podstawowy` and `poziom rozszerzony`, noting that rozszerzony is defined as podstawowy plus additions rather than as a separate tree.

#### M0 deliverable

A written comparison with three numbers per method, a recommendation, and the extracted curriculum seed file. Stop and wait.

---

### M1. Foundation

Repo structure, Docker Compose with Postgres, Alembic wired, config and secrets, curriculum tables, seeding from the hand-verified M0.5 file, `sources` seeded from `sources/MANIFEST.md`.

Seeding is idempotent and re-runnable. Do not have a model generate or infer licensing metadata; it comes from the manifest, which is authored by hand.

Tests: curriculum hierarchy, prerequisite cycle detection against a deliberately introduced loop, seed idempotency. Stop.

---

### M2. Ingestion

Source documents, the extraction pipeline in whichever form M0 justified, semantic chunking, figure extraction, provenance preservation, job system with a worker, synthetic fixture corpus, tests.

Gate: one real arkusz ingests end to end with page numbers, exercise numbers, and figures intact, and its exercise count matches its marking scheme. Stop.

---

### M3. Mapping and review

Mapping agent with confidence, review queue backend, review UI, dashboard skeleton with curriculum tree and source pages.

Gate: I can approve and reject mappings by keyboard without touching the mouse. Stop.

---

### M4. Knowledge

Knowledge agent, concepts, formulas, methods, examples, objectives, misconceptions, source attribution, conflict and gap flagging, dedupe and merge, knowledge spec assembly and hashing. Stop.

---

### M5. Exercises and verification

Exercise extraction and generation, SymPy verification in a sandboxed subprocess, answer representations, marking-scheme cross-checks, auto-verification rate metrics. Stop.

---

### M6. Episode and scene planning

Planner agent, four episode structures, duration model, scene plans, Scene Spec v1 schema exported to `contracts/`, QA checks, episode pages in the dashboard. Stop.

---

### M7. Full-path validation

One topic taken from raw source to a QA-passing scene plan for all four episode types, using the synthetic corpus plus one real arkusz.

Produce a preprocessing report: documents, pages, chunks, topics, concepts, formulas, exercises, misconceptions, figures, source references, unmapped material, ambiguous material, conflicts, and items requiring review.

Only after M7 do we discuss mass processing of textbooks.

---

## 18. TESTING

Automated tests for: curriculum hierarchy and prerequisite cycles, seed idempotency, source reference integrity, chunk provenance survival, Polish diacritic assertion against a deliberately corrupted fixture, extraction schema conformance, mapping status transitions, merge reversibility including the variant-group exclusion, exercise verification including deliberately wrong answers that must be caught, knowledge spec assembly and hash stability, episode and scene generation, duration estimation, QA rules, job retry semantics, and Scene Spec schema conformance.

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