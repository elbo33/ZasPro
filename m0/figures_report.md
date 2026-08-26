# M0.4 — Figure routes and corpus inventory

Counts and outcomes, not a pass/fail. LibreOffice headless required for the WMF and Word-shape routes.

## Corpus figure inventory

| document | raster media | WMF media | `<w:drawing>` total | chrome | task shapes |
|---|---|---|---|---|---|
| `MMAP-P0-660-A-2605-arkusz.docx` | 4 (3 body) | 1 (1 body) | 18 | 10 | 8 |
| `Informator_EM2024_matematyka_pp_660.docx` | 0 (0 body) | 0 (0 body) | 25 | n/a | n/a* |

\* The chrome/task split of `<w:drawing>` uses the arkusz's `Zadanie N.` … `Koniec` structure. The informator (theory + worked examples + numbered `Rysunek`) needs its own structure to split; that is M2. Its 25 body drawings are content figures — none is running chrome.

**The corpus has no task raster and no task WMF.** Every raster and the one WMF in both Track A DOCX files is chrome — the cover security image, the running-footer graphic, the header barcode. Every *task* figure is a Word-drawn shape that pandoc drops silently.

Arkusz task figures (Zadanie -> `<w:drawing>` count): {'12': 1, '13': 1, '18': 1, '19': 1, '20': 1, '21': 1, '27': 1, '32': 1}
Informator: 25 body drawings, all content figures (per-exercise attribution deferred to M2).

## Route 1 — raster (`pandoc --extract-media`)

Works. Extracts `.jpeg` / `.png` to a per-document `media/` dir. No task raster exists in this corpus, so nothing to attach; the mechanism is confirmed against the chrome images. **Failure mode:** without `--extract-media` pandoc emits `\includegraphics{media/imageN.jpeg}` for files it never writes (already guarded in `pandoc_convert`).

## Route 2 — WMF (LibreOffice `--convert-to png`)

- `image2.wmf` -> `image2.png` OK (6710 B)

Works — the arkusz's `image2.wmf` (a header barcode) rasterises crisply. **Failure mode not exercised here:** LibreOffice rasterises to a fixed canvas (816×1056 for this file) regardless of the metafile's own extent, so a real WMF diagram would need trimming to its ink bounds afterwards. No task WMF in the corpus to confirm line-weight / label fidelity on.

## Route 3 — Word-drawn shapes (DOCX → PDF → crop)

LibreOffice renders both DOCX files to PDF cleanly (`MMAP-P0-660-A-2605-arkusz.pdf`, `Informator_EM2024_matematyka_pp_660.pdf`). Shapes render faithfully — axes, tick labels, dashed guides, open/closed points, angle arcs all present (spot-checked Zadanie 12, Zadanie 21, informator Rysunek 1).

Auto-crop: scope to the task's own band (between its `Zadanie N.` marker and the next), drop primitives that sit on a body-text baseline (statement math), take the vector-primitive bbox of the rest, union in nearby single-glyph labels. **All 8 arkusz figures are fully captured and reviewable.** Residual imperfections are cosmetic, listed below.

| task | PDF page | bbox (pt) | crop | warnings |
|---|---|---|---|---|
| 12 | 6 | (66, 175, 524, 575) | `m0/figures/arkusz_zadanie_12.png` | dropped 5 in-text primitive(s) (statement math) |
| 13 | 7 | (73, 174, 409, 490) | `m0/figures/arkusz_zadanie_13.png` | dropped 3 in-text primitive(s) (statement math) |
| 18 | 9 | (65, 124, 479, 487) | `m0/figures/arkusz_zadanie_18.png` | dropped 10 in-text primitive(s) (statement math) |
| 19 | 10 | (65, 138, 392, 585) | `m0/figures/arkusz_zadanie_19.png` | clean |
| 20 | 11 | (65, 154, 431, 722) | `m0/figures/arkusz_zadanie_20.png` | clean |
| 21 | 12 | (65, 124, 458, 413) | `m0/figures/arkusz_zadanie_21.png` | clean |
| 27 | 16 | (65, 170, 517, 424) | `m0/figures/arkusz_zadanie_27.png` | dropped 4 in-text primitive(s) (statement math) |
| 32 | 18 | (65, 521, 392, 651) | `m0/figures/arkusz_zadanie_32.png` | clean |

**Failure modes named:**

1. **Shape text is real PDF text.** LibreOffice renders a shape's labels as selectable text, so a figure is *not* a blank band — a naive 'largest text gap' crop misses it. Vector primitives are the right signal.
2. **Cross-exercise primitives.** Fraction bars / radical vinculums in a *neighbouring* exercise on the same page are `line`/`rect` primitives and blew the bbox vertically. Fixed by scoping to the task band before taking the bbox.
3. **In-statement math primitives.** A radical/fraction bar in the task's *own* statement is in-band. Fixed by dropping primitives that share a baseline with a run of words (the `dropped N in-text` warnings). A crude size heuristic; a real solution keys on the drawing's XML identity (M2).
4. **Trailing statement lines with no primitives.** The band starts at the marker, so plain-text lines between the marker and the figure (e.g. Zadanie 27's 'Oblicz… / Zapisz…') sit inside the crop. Harmless — the figure is complete — but not tight. Needs the figure's top edge from its own primitives, not the band top.
5. **Edge labels sit outside the vector extent.** Vertex letters at a triangle's corners are past the last drawn line; the label-union step recovers most, wide placements still clip a glyph.
6. **`<w:object>` / VML is invisible to the `<w:drawing>` count.** The arkusz's WMF rides an OLE `<w:object>` with a `<v:imagedata>` fallback, which `figures.count_drawings_by_task` does not see. Chrome here, but M2's counter should also scan `<w:object>` / `<v:imagedata>`.
7. **No per-shape extent used yet.** The DOCX carries each drawing's `<wp:extent>` in EMU; mapping that to PDF coordinates would beat the primitive-bbox heuristic. Deferred to M2.

## Verdict

All three routes function. The corpus figure load is entirely Route 3: 8 arkusz task shapes + 25 informator content shapes, recovered by LibreOffice DOCX→PDF. The primitive-bbox crop, once scoped to the task's own band, is good enough to review; items 2–5 are the cleanup needed before it is production-clean (M2).
