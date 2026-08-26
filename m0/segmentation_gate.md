# M0.2 — Segmentation gate

**PASS** — `MMAP-P0-660-A-2605-arkusz.docx` vs `MMAP-P0-100-2605-zasady.pdf`

- pandoc: `pandoc 3.10.2`
- boilerplate strip: head: 6033 chars removed (longtable×3, includegraphics×3, enumerate×2); tail: 601 chars removed (Koniec sentinel found)
- chunks emitted: 41 (4 parents + 37 pointed leaf tasks)

| | arkusz | marking scheme |
|---|---|---|
| pointed tasks | 37 | 37 |
| total points | 50 | 50 |

Counts and point values match exactly. Segmentation is trustworthy for this paper.

## Figure completeness (SPEC: silent figure loss is a data error)

`<w:drawing>` in DOCX body: 18 total — 10 cover / header / footer chrome, 8 in 8 figure-bearing task region(s).

**⚠ 12 chunk(s) expect a figure that was not extracted** (8 own the figure, the rest inherit it via a parent stem). Pandoc drops Word-drawn shapes; extraction is M0.4. Until then every one of these is knowingly incomplete:

| task | expected | extracted |
|---|---|---|
| 12 (parent) | 1 | 0 |
| 12.1 | 1 | 0 |
| 12.2 | 1 | 0 |
| 13 (parent) | 1 | 0 |
| 13.1 | 1 | 0 |
| 13.2 | 1 | 0 |
| 18 | 1 | 0 |
| 19 | 1 | 0 |
| 20 | 1 | 0 |
| 21 | 1 | 0 |
| 27 | 1 | 0 |
| 32 | 1 | 0 |

> Marking scheme was extracted from PDF (`pdftotext`), not a DOCX sibling (none exists). Deterministic for this born-digital Word PDF, but noted per the M0.1 exception.
