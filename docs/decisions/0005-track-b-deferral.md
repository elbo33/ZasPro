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

## What M0.5 did establish (see m0/pdf_audit.md)

All six PDF sources are born-digital with a real text layer (353–1,799 non-space
chars/page, well above the ~100 image-only threshold). Polish diacritics
survive extraction: ratios 5.3–6.3% (normal for maths documents; prose is
8–12%), with large, proportionate `ł` counts — no silent `ToUnicode` / WinAnsi
corruption. The two Track B PDFs specifically — `DU_programowej_2024.pdf` (the
curriculum authority) and the formula sheet — extract cleanly with `pdftotext`.

Consequence: when Track B ingestion is built, the podstawa programowa needs only
plain text extraction plus semantic chunking, not OCR or a VLM. Textbooks are
the open question, and the one the survey exists for.

## Also discarded here

`matematyka.pdf` (CKE `_OD_2015` maths-only podstawa extract) — checked against
Dz.U. 2024 poz. 1019 in M0.6 and found to predate the 2024 amendment. Not a
Track B source; see `m0/curriculum_notes.md`.
