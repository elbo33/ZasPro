# Dependency licence log

SPEC §3: record a licence here **before** adding any extraction dependency.
This project may eventually carry paid content, so licence terms are
load-bearing, not paperwork.

## Python packages (M0)

| package | version | licence | role | notes |
|---|---|---|---|---|
| pydantic | 2.13.x | MIT | typed boundaries at every module line | pydantic-core (MIT) |
| pdfplumber | 0.11.x | MIT | PDF char geometry + text for M0.5 audit and M0.6 curriculum extraction | depends on pdfminer.six (MIT), pypdfium2 (BSD-3 / Apache-2.0), Pillow (MIT-CMU) |
| sympy | 1.14.x | BSD-3-Clause | M0.3 naive-parse characterisation; symbolic verification from M5 | in the SPEC §3 stack ("symbolic maths are Python-native"). mpmath (BSD) |
| lark | 1.x | MIT | backend for `sympy.parsing.latex.parse_latex(..., backend="lark")` — avoids the antlr4 runtime | pure Python |
| pytest | 9.x | MIT | tests | dev-only |
| hatchling | (build) | MIT | build backend | build-only |

## Python packages (M1)

All four are named in the SPEC §3 stack; these are the concrete versions.

| package | version | licence | role | notes |
|---|---|---|---|---|
| SQLAlchemy | 2.0.x | MIT | typed ORM (SPEC §3) | — |
| Alembic | 1.19.x | MIT | migrations (SPEC §3) | Mako (MIT) for templates |
| psycopg[binary] | 3.3.x | LGPL-3.0 | PostgreSQL driver for SQLAlchemy | LGPL, used unmodified as a library — no copyleft reach into our code. `-binary` ships the libpq wheel. |
| pydantic-settings | 2.15.x | MIT | env / `.env` config (SPEC §3: "Secrets in environment variables") | python-dotenv (BSD) |
| PyYAML | 6.x | MIT | load `seeds/curriculum_matematyka.yaml` | — |

## System tools (M0, invoked as subprocesses)

| tool | licence | role | notes |
|---|---|---|---|
| pandoc | GPL-2.0-or-later | DOCX→LaTeX (ADR 0001) | subprocess only; GPL does not reach our code. v3.10.2 |
| poppler (`pdftotext`, `pdfinfo`, `pdffonts`) | GPL-2.0 | marking-scheme text for the M0.2 gate; M0.5 text-layer / diacritic / math-character audit | subprocess only. v26.08 |
| TeX (`pdflatex`) | LPPL / mixed | `test_seed_latex.py` compiles every `statement_latex` in the curriculum seed | subprocess only, dev/CI. Test **skips** if absent, so not a hard dependency; run it where TeX exists to get the guarantee. |
| LibreOffice headless (`soffice`) | MPL-2.0 | M0.4 figure work: WMF render, DOCX→PDF for Word-drawn shapes | installed; not yet exercised (M0.4) |
| uv | Apache-2.0 OR MIT | env + dependency manager, standalone CPython 3.12 (ADR 0002) | single static binary, no services |

## Python packages (M3)

FastAPI and the Next.js dashboard are named in SPEC §3 and §16; adding them
executes that decision (see ADR 0009), it does not make a new one.

| package | version | licence | role | notes |
|---|---|---|---|---|
| anthropic | 1.1.x | MIT | Mapping Agent LLM calls (`claude-opus-5`) — SPEC §12 | only imported on the `ClaudeMappingAgent` path; the offline `StubMappingAgent` needs neither the package's client nor a key |
| FastAPI | 0.141.x | MIT | the internal API (SPEC §3, §16) | Starlette (BSD-3), pydantic already present |
| uvicorn | 0.52.x | BSD-3-Clause | ASGI server to run the API in dev | plain build, no `[standard]` extras (no uvloop/httptools pulled) |
| httpx | 0.28.x | BSD-3-Clause | **dev only** — `fastapi.testclient` transport for `tests/test_api_review.py` | httpcore (BSD-3) |

## Node packages (M3 — `dashboard/`)

Isolated in `dashboard/`, its own `package.json`, never imported by Python. Not
installed in CI for the Python test job.

| package | version | licence | role |
|---|---|---|---|
| next | 14.2.x | MIT | App Router dashboard (SPEC §16) |
| react / react-dom | 18.3.x | MIT | — |
| typescript + `@types/*` | 5.5.x | MIT / Apache-2.0 | dev only |

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
