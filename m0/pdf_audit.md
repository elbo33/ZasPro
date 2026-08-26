# M0.5 — PDF text-layer and Polish-diacritic audit

`pdftotext` / `pdfinfo` / `pdffonts` over `sources/raw/*.pdf`. Image-only if < 100 non-space chars/page. Polish prose runs ~8–12% diacritics among letters; < 3% on a text-bearing document means a broken `ToUnicode` CMap (silent). `ł` is the canary.

| file | pages | chars/page | text layer | diacritic ratio | `ł`+`Ł` | embedded fonts w/o ToUnicode |
|---|---|---|---|---|---|---|
| `DU_programowej_2024.pdf` | 524 | 1,799 | yes | 5.3% | 8,910 | 1 / 9 |
| `Informator_EM2024_matematyka_pp.pdf` | 158 | 956 | yes | 5.8% | 1,366 | 3 / 10 |
| `MMAP-P0-100-2605-zasady.pdf` | 42 | 1,065 | yes | 5.4% | 332 | 0 / 5 |
| `MMAP-P0-100-A-2605-arkusz.pdf` | 36 | 353 | yes | 6.3% | 125 | 2 / 8 |
| `matematyka.pdf` | 72 | 1,713 | yes | 6.2% | 1,231 | 0 / 8 |
| `wybrane_wzory_matematyczne_EM2023.pdf` | 36 | 737 | yes | 6.0% | 150 | 3 / 10 |

## Assertions

- **Text layer:** 6/6 PDFs have a real text layer.
- **Diacritics:** 6/6 text-bearing PDFs clear the 2% corruption floor. Ratios cluster at 5–6%, normal for maths documents (prose is 8–12%; formulae and numerals dilute it). `ł` counts are large and proportionate — no silent WinAnsi truncation.
- **ToUnicode:** the table column counts font *names* for which **no** embedded instance has a ToUnicode CMap. Names with no good instance anywhere: `DU_programowej_2024.pdf` → ArialMT; `Informator_EM2024_matematyka_pp.pdf` → Calibri, Calibri-Bold, Cambria-Italic; `MMAP-P0-100-A-2605-arkusz.pdf` → Calibri, Cambria; `wybrane_wzory_matematyczne_EM2023.pdf` → Calibri, OpenSans-Bold, OpenSans-Light

**Overall: no image-only sources, no diacritic corruption. The Track B PDFs (`DU_programowej_2024.pdf`, `matematyka.pdf`) and the formula sheet are born-digital with clean, extractable Polish text.**

## Scope

Per SPEC M0.5, that is the whole audit. No extractor comparison was run — it is work for whenever textbooks arrive, and the landscape will have moved. The survey in `docs/sources.md` Part B is the starting point; the deferral is recorded in `docs/decisions/0005-track-b-deferral.md`.
