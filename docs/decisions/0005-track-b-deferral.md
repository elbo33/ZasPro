# ADR 0005 — Track B (unstructured PDF) extraction is deferred

Status: accepted (M0.5)
Date: 2026-08-26

## Context

Track B is the podstawa programowa and any textbooks that arrive later — PDF
sources with no CKE `_660.docx` sibling. SPEC M0.5 limited M0 to two questions
about them and explicitly forbade an extractor comparison ("It is work for
whenever textbooks arrive, and the landscape will have moved").

## Decision

No PDF-extractor comparison is run in M0. Track B ingestion is deferred until
textbooks actually arrive. The survey in `docs/sources.md` Part B (MinerU,
Marker, Docling, olmOCR, Mathpix, the olmOCR-Bench / OmniDocBench / PureDocBench
benchmarks) is the starting point at that time — re-checked, since the field
moves monthly.

## What M0.5 established (see m0/pdf_audit.md)

All six PDF sources are born-digital with a real text layer (353–1,799 non-space
chars/page). Polish **prose** survives extraction everywhere: diacritic ratios
5.3–6.3% with large, proportionate `ł` counts.

But the **maths does not** in the curriculum authority. `DU_programowej_2024.pdf`
(and the superseded `matematyka.pdf`) set their maths in a font whose ToUnicode
doubles every italic variable and collapses stacked fractions; `pdftotext`
turned `½·a·b` into `2·a·b` and `a/x` into `x`. The M0.5 diacritic check first
reported an all-clear because it only tested prose characters — a
math-character assertion was added afterwards (`math_alnum_stats`), and it
flags `DU` (54% doubled) and `matematyka.pdf` (56% + PUA). The formula sheet
`wybrane_wzory_matematyczne_EM2023.pdf` sits below the flag threshold but M2
should spot-check it.

Consequence: when Track B ingestion is built, the podstawa programowa's **prose**
needs only `pdftotext` plus semantic chunking, but its **formulae** need a
different route — a DOCX sibling, maths-aware OCR/VLM over rendered pages, or
hand transcription (M0.6 hand-transcribed the ~20 curriculum formulae). Run the
math-character assertion on every new Track B source before ingesting it.

## Also discarded here

`matematyka.pdf` (CKE `_OD_2015` maths-only podstawa extract) — checked against
Dz.U. 2024 poz. 1019 in M0.6 and found to predate the 2024 amendment. Not a
Track B source; see `m0/curriculum_notes.md`.
