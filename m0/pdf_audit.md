# M0.5 — PDF text-layer, diacritic, and mathematical-character audit

`pdftotext` / `pdfinfo` / `pdffonts` over `sources/raw/*.pdf`.

- **text layer:** image-only if < 100 non-space chars/page.
- **diacritics:** Polish prose runs 8–12% diacritics among letters, maths documents ~5–6%; below 2% on a text-bearing document = broken `ToUnicode` on the prose font. `ł` is the canary.
- **math (added post-M0.6):** fraction of Mathematical Alphanumeric Symbols (U+1D400–U+1D7FF) emitted **doubled** (`𝑥𝑥` for `𝑥`), plus any Private-Use glyphs. A doubled maths font also collapses stacked fractions and superscripts. Flag at ≥ 15% doubling or any PUA.

| file | pages | chars/page | text layer | diacritic ratio | `ł`+`Ł` | fonts w/o ToUni | math-alnum (doubled / total) | PUA |
|---|---|---|---|---|---|---|---|---|
| `DU_programowej_2024.pdf` | 524 | 1,799 | yes | 5.3% | 8,910 | 1 / 9 | 209 / 386 (54%) ⚠ | 0 |
| `Informator_EM2024_matematyka_pp.pdf` | 158 | 956 | yes | 5.8% | 1,366 | 3 / 10 | 5 / 4847 (0%) | 0 |
| `MMAP-P0-100-2605-zasady.pdf` | 42 | 1,065 | yes | 5.4% | 332 | 0 / 5 | 0 / 1129 (0%) | 0 |
| `MMAP-P0-100-A-2605-arkusz.pdf` | 36 | 353 | yes | 6.3% | 125 | 2 / 8 | 0 / 296 (0%) | 0 |
| `matematyka.pdf` | 72 | 1,713 | yes | 6.2% | 1,231 | 0 / 8 | 135 / 240 (56%) ⚠ | 115 ⚠ |
| `wybrane_wzory_matematyczne_EM2023.pdf` | 36 | 737 | yes | 6.0% | 150 | 3 / 10 | 41 / 3045 (1%) | 0 |

## Assertions

- **Text layer:** 6/6 PDFs have a real text layer.
- **Diacritics:** 6/6 text-bearing PDFs clear the 2% floor (ratios 5–6%, `ł` counts large and proportionate — the **prose** font is fine everywhere).
- **Mathematical characters:** **CORRUPT in `DU_programowej_2024.pdf` (54% of 386 math-alnum doubled), `matematyka.pdf` (56% of 240 math-alnum doubled, 115 PUA).** The maths font's ToUnicode maps each italic variable to a two-codepoint sequence, so `pdftotext` emits `𝑥𝑥` for `𝑥`; stacked fractions and superscripts collapse alongside (`½ · a · b` → `2 ⋅ a ⋅ b`, `a/x` → `x`, `sin α / cos α` → `cos α`). Prose is unaffected because it uses a different font with a correct ToUnicode.
- **ToUnicode (font table):** the column counts font *names* with no ToUnicode instance at all. The prose fonts (Times/Arial/Calibri) always resolve; the flagged `Cambria`/`CambriaMath` subsets are the maths font — consistent with the math-character finding above.

**Overall:**

- Text layer: OK (6/6).
- Polish prose: OK (6/6). **This is what M0.5 originally reported, and it was a false all-clear** — it never tested mathematical characters.
- Mathematics: **CORRUPT** in `DU_programowej_2024.pdf`, `matematyka.pdf`. `DU_programowej_2024.pdf` is the curriculum authority (M0.6 seed source); its maths cannot be trusted from `pdftotext` and the seed's formulae are being hand-transcribed from the rendered PDF instead (`seeds/curriculum_matematyka_formulas_review.md`). `matematyka.pdf` is superseded. The formula sheet `wybrane_wzory_matematyczne_EM2023.pdf` — the main maths-heavy Track B ingestion target — is **below the flag threshold** (see table); M2 should still spot-check it before ingesting.

## For M2

Any Track B PDF that carries a doubled maths font must not be text-mined for formulae with `pdftotext`. Options in order of preference: the document's DOCX sibling if one exists; a maths-aware OCR / VLM over rendered pages; or hand transcription for small volumes (as M0.6 did). Run this audit on every new Track B source before ingesting it.

## Scope

No extractor comparison was run (ADR 0005). The survey in `docs/sources.md` Part B is the starting point when textbooks arrive.
