# ADR 0001 — Pandoc for DOCX→LaTeX, not a custom OMML converter

Status: accepted (M0.2)
Date: 2026-08-26

## Context

CKE publishes `_660.docx` accessibility exports ("czarnodruk") of the
informatory and every exam paper. The M0 question is how to get exercise text
and mathematics out of them.

## Decision

Convert with **pandoc 3.10.2**, invoked as a subprocess
(`zaspro.extraction.pandoc_convert`), always with `--extract-media`. No custom
OMML→LaTeX code. This confirms SPEC decision 7.

## Evidence (SPEC §2a spike + M0.2 verification on real files)

- The `_660.docx` exports carry **native OMML** (`<m:oMath>`), not images or
  flattened text. Measured in `word/document.xml`:
  `Informator_EM2024_matematyka_pp_660.docx` → 994 `oMath`, 212 display
  (`oMathPara`), 25 Word drawings, 0 media files;
  `MMAP-P0-660-A-2605-arkusz.docx` → 284 `oMath`, 9 display, 18 drawings, 5
  media files. (SPEC §2a originally read 1386 / 392 / 298 — a raw `<m:oMath`
  substring count that also caught the `<m:oMathPara` / `<m:oMathParaPr`
  prefixes. `1386 − 392 = 994`, `298 − 14 = 284`; drawings and media were
  always exact. SPEC §2a and `m0/corpus_split.md` now hold the corrected
  element counts. No decision changes.)
- Pandoc converts both files cleanly: Polish diacritics intact, hyperlinks
  preserved, equations accurate for **display**.
- Exercise structure survives as parseable text: `Zadanie N. (0--M)`, parents
  as bare `Zadanie N.`, subtasks as `Zadanie N.M. (0--M)`.
- M0.2 gate: the segmented `MMAP-P0-660-A-2605` matches its marking scheme
  exactly — 37 pointed tasks, 50 points. Zero segmentation errors.

## Known limitation (not a reason to reject pandoc)

Pandoc's LaTeX is **visually faithful and semantically unsafe** — e.g.
`\log_{8}{4 - \log_{8}32}` renders correctly but parses wrongly. Rendering is
the right fidelity check for extraction and the wrong input for verification.
This is why raw and normalised LaTeX are separate fields; the normalisation
layer is M5, scoped from the M0.3 study.

## Alternatives rejected

- **Custom OMML→LaTeX converter.** Months of work to reproduce a mature,
  correct pandoc reader. No upside.
- **PDF extraction of the `100` papers** (Mathpix / VLM / pdfplumber). Non-
  deterministic, costs per page, and unnecessary when a structured sibling
  exists. Remains the Track B approach for sources with no DOCX.

## Consequences

- Track A extraction has **no confidence score**: `confidence = NULL` means
  deterministic (SPEC §5). Deterministic content skips the review queue.
- pandoc is a hard runtime dependency of the pipeline (GPL-2.0+, subprocess
  only — see `dependencies.md`).
- Word-drawn shapes are dropped silently by pandoc — 8 of this arkusz's 18
  body `<w:drawing>` elements belong to tasks (12, 13, 18, 19, 20, 21, 27, 32).
  M0.2 now counts `<w:drawing>` per task range and records it as
  `ExerciseChunk.expected_figure_count`, so a lost figure is a visible
  `figures_incomplete` flag rather than a silent gap. Actual recovery of those
  shapes is M0.4.
