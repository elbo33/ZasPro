# ADR 0008 — Podstawowy only, for now

Status: accepted (after M2 corpus ingestion)
Date: 2026-08-27

## Context

The M0.6 curriculum seed covers both levels: 73 podstawowy + 46 rozszerzony
requirements. The M2 corpus went in and established:

* Every Formuła 2023 rozszerzony exam paper and marking scheme is **PDF only**.
  There is **no czarnodruk (`_660`) DOCX** for rozszerzony in any session
  checked (2024, 2025). Version B podstawowy papers are likewise PDF only.
* So all rozszerzony material is Track B — the non-deterministic PDF path,
  deferred under ADR 0005. Roughly half the curriculum tree has no
  deterministic source.
* The podstawowy Track A path works end to end: 3/3 corpus arkusze
  (maj-2024, -2025, -2026) pass the marking-scheme gate with no change to the
  boilerplate stripper or the segmenter.

## Decision

**Build the podstawowy course. Rozszerzony stays deferred.**

* Every Matura candidate sits the podstawowy exam. Rozszerzony is an
  additional paper taken by a subset.
* A complete single-level course is more useful than a two-level one where
  half the topics have no content.
* The deterministic path already works for podstawowy; rozszerzony would need
  the Track B PDF pipeline first, which is a milestone of its own.

## What this does and does not change

* The **46 rozszerzony topics stay in `topics`**, seeded, `level =
  rozszerzony`, correct against Dz.U. 2024. They simply carry no exercises,
  concepts, or episodes. The curriculum tree remains whole.
* The rozszerzony informator (`Informator_EM2024_matematyka_pr_660.docx`) and
  the rozszerzony arkusze stay in `sources/MANIFEST.md` and get
  `source_documents` rows (`extraction_status = pending`). They are future
  material, not deleted.
* Downstream milestones (M3 mapping, M4 knowledge, M6 planning) operate on
  podstawowy topics only until rozszerzony has a source path.
* Revisit when the Track B PDF pipeline exists, or if a rozszerzony czarnodruk
  DOCX appears in a future session.

## Consequence for M3

M3's review queue and mapping agent work against podstawowy exercises only —
~105 leaf tasks over 73 requirements. The `m2/exercise_coverage.md` histogram
(3 of 73 requirements at the EXERCISES-format bar of 5 exercises) is the
baseline: the queue is being built against a corpus that is small but real, and
its behaviour at that scale is the point of M3.
