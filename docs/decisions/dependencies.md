# Dependency licence log

SPEC §3: record a licence here **before** adding any extraction dependency.
This project may eventually carry paid content, so licence terms are
load-bearing, not paperwork.

## Python packages (M0)

| package | version | licence | role | notes |
|---|---|---|---|---|
| pydantic | 2.13.x | MIT | typed boundaries at every module line | pydantic-core (MIT) |
| pdfplumber | 0.11.x | MIT | PDF char geometry + text for M0.5 audit and M0.6 curriculum extraction | depends on pdfminer.six (MIT), pypdfium2 (BSD-3 / Apache-2.0), Pillow (MIT-CMU) |
| pytest | 9.x | MIT | tests | dev-only |
| hatchling | (build) | MIT | build backend | build-only |

## System tools (M0, invoked as subprocesses)

| tool | licence | role | notes |
|---|---|---|---|
| pandoc | GPL-2.0-or-later | DOCX→LaTeX (ADR 0001) | subprocess only; GPL does not reach our code. v3.10.2 |
| poppler (`pdftotext`, `pdfinfo`, `pdffonts`) | GPL-2.0 | marking-scheme text for the M0.2 gate; M0.5 text-layer / diacritic / ToUnicode audit | subprocess only. v26.08 |
| LibreOffice headless (`soffice`) | MPL-2.0 | M0.4 figure work: WMF render, DOCX→PDF for Word-drawn shapes | installed; not yet exercised (M0.4) |
| uv | Apache-2.0 OR MIT | env + dependency manager, standalone CPython 3.12 (ADR 0002) | single static binary, no services |

## What covers the M0.5 PDF audit now that PyMuPDF is out

The audit that a maths-first PDF library would have done is split between two
tools already listed:

- **poppler** — `pdftotext` for chars-per-page, `pdfinfo` for page counts,
  `pdffonts` for `ToUnicode` CMap presence (the silent-diacritic-corruption
  check). This is exactly the toolset the SPEC M0.5 / sources.md A6 scripts
  assume.
- **pdfplumber** — per-character `size`/`top`/`fontname` geometry for the
  diacritic-ratio assertion and any superscript/boundary heuristics.

No maths-first extractor (Mathpix, MinerU, a VLM) is needed for Track A, which
is deterministic from the DOCX.

## Rejected

| candidate | reason |
|---|---|
| **PyMuPDF / pymupdf4llm** | AGPL-3.0 (commercial licence sold separately). This project may carry paid content; AGPL obligations on a networked service are a poor fit and the paid licence is an unnecessary cost when poppler + pdfplumber cover the need. |
| datalab.to projects (Marker, Surya) | some attach revenue conditions to otherwise-open licences (Surya weights: free only under $2M revenue). Not needed for Track A. Revisit only if Track B textbook extraction ever requires them. |

## Still to decide (M0.4)

Whether LibreOffice alone handles WMF conversion adequately, or whether
`imagemagick` / `libwmf` are also needed. Deferred until M0.4 tests real
output quality — three tools for one job tends to become permanent.
