# ADR 0004 — Figure extraction routes per format

Status: accepted (M0.4)
Date: 2026-08-26

## Context

Track A DOCX files carry figures in three forms. Pandoc emits `\includegraphics`
only for embedded raster/WMF media; it drops Word-drawn shapes silently. SPEC
M0.4 required establishing a route for each and naming what fails.

## Corpus finding (measured, see m0/figures_report.md)

| format | arkusz `MMAP-P0-660-A-2605` | informator `_pp_660` |
|---|---|---|
| raster media (`.jpeg`/`.png`) | 4 — **all chrome** (cover, footer) | 0 |
| WMF media | 1 — **chrome** (header barcode) | 0 |
| Word-drawn shapes (`<w:drawing>`) | 18 total; **8 are task figures** (Zadania 12, 13, 18, 19, 20, 21, 27, 32) | 25, all content figures |

**Every task figure in the Track A corpus is a Word-drawn shape.** There is no
task raster and no task WMF. The raster/WMF routes are confirmed working but
have nothing but chrome to carry here.

## Decision

| format | route | status |
|---|---|---|
| raster | `pandoc --extract-media` (already the default in `pandoc_convert`) | works |
| WMF | LibreOffice headless `--convert-to png` | works (barcode rasterises crisply); no task WMF to test line/label fidelity on |
| Word shape | LibreOffice `--convert-to pdf`, then crop the figure region from the task's band with pdfplumber vector primitives (`lines`+`curves`+`rects`), unioned with edge labels | works — all 8 arkusz task figures recovered and reviewable |

`figures.count_drawings_by_task` records `<w:drawing>` count per task as
`ExerciseChunk.expected_figure_count`, so a dropped figure is a visible
`figures_incomplete` flag (ADR 0001), not a silent gap.

## Failure modes (named, deferred to M2)

1. Shape labels render as real PDF text — a "blank band" crop misses the figure; vector primitives are the right signal.
2. Fraction/radical bars in *neighbouring* exercises are primitives too — fixed by scoping the bbox to the task's own marker→next-marker band.
3. Fraction/radical bars in the task's *own* statement — dropped heuristically (primitive shares a baseline with word runs); a real fix keys on the drawing's XML identity.
4. Plain-text statement lines between the marker and the figure sit inside the crop (figure still complete, box not tight) — needs the figure top edge from its own primitives.
5. Edge labels (triangle vertices) past the last drawn line — label-union recovers most; wide placements clip a glyph.
6. `<w:object>` / VML (the arkusz WMF) is invisible to the `<w:drawing>` counter — M2's counter should also scan `<w:object>` / `<v:imagedata>`.
7. Per-shape `<wp:extent>` (EMU) is not used yet — mapping it to PDF coordinates would beat the primitive-bbox heuristic.

## Consequence

LibreOffice headless is a hard dependency for figure extraction from M2 on
(MPL-2.0; see `dependencies.md`). `imagemagick` / `libwmf` were **not** needed —
LibreOffice alone covers WMF and DOCX→PDF. Revisit only if a real WMF task
figure turns up and LibreOffice's rendering of it proves poor.
