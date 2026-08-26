"""M0.4 figure routes: raster, WMF, and Word-drawn shapes.

Findings from the Track A corpus (see m0/figures_report.md):

* **raster** (`--extract-media`): works, but every raster in the two Track A
  DOCX files is chrome (cover / running footer). Zero task rasters.
* **WMF** (LibreOffice `--convert-to png`): works (the arkusz's one WMF, a
  header barcode, renders crisply). Also chrome. Zero task WMF.
* **Word-drawn shapes** (`<w:drawing>` / `<mc:AlternateContent>`): pandoc drops
  them entirely, and they are *every* task figure in the corpus. Recovered by
  rendering the DOCX to PDF with LibreOffice, then cropping the figure region
  with pdfplumber vector primitives.

LibreOffice headless is required for the last two routes.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

_SOFFICE_CANDIDATES = (
    os.environ.get("SOFFICE", ""),
    "soffice",
    "libreoffice",
    "/Applications/LibreOffice.app/Contents/MacOS/soffice",
)


class LibreOfficeNotFound(RuntimeError):
    pass


def soffice_bin() -> str:
    for cand in _SOFFICE_CANDIDATES:
        if cand and (shutil.which(cand) or Path(cand).is_file()):
            return cand
    raise LibreOfficeNotFound(
        "LibreOffice headless not found (set $SOFFICE or install libreoffice)"
    )


def _run_soffice(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        [soffice_bin(), "--headless", *args],
        capture_output=True,
        text=True,
        timeout=180,
    )


def convert(src: Path, out_dir: Path, fmt: str) -> Path:
    """Convert *src* to *fmt* (e.g. ``"pdf"``, ``"png"``) under *out_dir*."""

    src, out_dir = Path(src), Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    proc = _run_soffice(["--convert-to", fmt, "--outdir", str(out_dir), str(src)])
    result = out_dir / f"{src.stem}.{fmt}"
    if proc.returncode != 0 or not result.is_file():
        raise RuntimeError(f"soffice --convert-to {fmt} failed for {src.name}: {proc.stderr.strip()}")
    return result


def docx_to_pdf(docx: Path, out_dir: Path) -> Path:
    return convert(docx, out_dir, "pdf")


def task_page_map(pdf_path: Path, tasks: list[str]) -> dict[str, int]:
    """1-indexed PDF page for each ``Zadanie N[.M].`` marker (first occurrence)."""

    import re

    import pdfplumber

    wanted = {t: re.compile(rf"^Zadanie\s+{re.escape(t)}\.(?:\s|$)", re.MULTILINE) for t in tasks}
    found: dict[str, int] = {}
    with pdfplumber.open(str(pdf_path)) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            for task, pat in wanted.items():
                if task not in found and pat.search(text):
                    found[task] = i
    return found


@dataclass(frozen=True)
class FigureCrop:
    task: str
    page: int
    bbox: tuple[float, float, float, float]
    png: Path
    warnings: list[str]


def _marker_y(page, task: str) -> float | None:
    """Top y of the line that opens ``Zadanie <task>.`` on this page."""

    import re

    pat = re.compile(rf"^Zadanie\s+{re.escape(task)}\.(?:\s|$)")
    lines: dict[float, list[dict]] = {}
    for w in page.extract_words():
        lines.setdefault(round(w["top"]), []).append(w)
    for top in sorted(lines):
        text = " ".join(w["text"] for w in sorted(lines[top], key=lambda w: w["x0"]))
        if pat.match(text):
            return min(w["top"] for w in lines[top])
    return None


def crop_task_figure(
    pdf_path: Path,
    page_number: int,
    task: str,
    out_png: Path,
    *,
    next_task: str | None = None,
    resolution: int = 200,
) -> FigureCrop:
    """Crop the figure for *task* on *page_number* (1-indexed).

    The figure sits between this task's marker line and the next marker (or the
    page bottom). Restricting to that band first is what keeps fraction bars and
    rules from *neighbouring* exercises out of the vector-primitive bbox — the
    dominant M0.4 failure mode. Remaining edge cases are returned as warnings.
    """

    import pdfplumber

    warnings: list[str] = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        page = pdf.pages[page_number - 1]

        band_top = _marker_y(page, task)
        if band_top is None:
            warnings.append("task marker not located on page; using full page height")
            band_top = 0.0
        else:
            band_top += 4  # drop the marker line itself

        band_bot = page.height
        if next_task:
            ny = _marker_y(page, next_task)
            if ny is not None:
                band_bot = ny

        def in_band(o) -> bool:
            cy = (o["top"] + o["bottom"]) / 2
            return band_top <= cy <= band_bot

        prims = [o for o in (list(page.lines) + list(page.curves) + list(page.rects)) if in_band(o)]
        if not prims:
            raise RuntimeError(f"{task}: no vector primitives in task band on page {page_number}")

        # Drop primitives that sit on a body-text baseline inside the band — a
        # radical vinculum or fraction bar in the task's own statement text.
        # A drawn figure element rarely shares a row with a run of words.
        word_rows = [(w["top"], w["bottom"]) for w in page.extract_words()]

        def on_text_row(o) -> bool:
            cy = (o["top"] + o["bottom"]) / 2
            wide = abs(o["x1"] - o["x0"]) < 60 and abs(o["bottom"] - o["top"]) < 6
            return wide and any(t - 2 <= cy <= b + 2 for t, b in word_rows)

        figure_prims = [o for o in prims if not on_text_row(o)]
        if len(figure_prims) >= 5:
            if len(figure_prims) < len(prims):
                warnings.append(f"dropped {len(prims) - len(figure_prims)} in-text primitive(s) (statement math)")
            prims = figure_prims

        x0 = min(min(o["x0"], o["x1"]) for o in prims)
        x1 = max(max(o["x0"], o["x1"]) for o in prims)
        y0 = min(min(o["top"], o["bottom"]) for o in prims)
        y1 = max(max(o["top"], o["bottom"]) for o in prims)

        # union in edge labels within the band (vertex letters past the last line)
        for w in page.extract_words():
            wx, wy = (w["x0"] + w["x1"]) / 2, (w["top"] + w["bottom"]) / 2
            if band_top <= wy <= band_bot and x0 - 24 <= wx <= x1 + 24 and y0 - 20 <= wy <= y1 + 20:
                x0, x1 = min(x0, w["x0"]), max(x1, w["x1"])
                y0, y1 = min(y0, w["top"]), max(y1, w["bottom"])

        pad = 6
        bbox = (
            max(0, x0 - pad),
            max(band_top - 2, y0 - pad),
            min(page.width, x1 + pad),
            min(band_bot + 2, y1 + pad),
        )
        if bbox[2] - bbox[0] > page.width * 0.95:
            warnings.append("bbox spans full page width — stray rule in band")
        if bbox[3] - bbox[1] > (band_bot - band_top) * 0.98 and band_top > 0:
            warnings.append("bbox fills the whole task band — figure extent not isolated from text")
        if bbox[3] - bbox[1] < 40:
            warnings.append("bbox under 40pt tall — primitives may be sparse")

        out_png = Path(out_png)
        out_png.parent.mkdir(parents=True, exist_ok=True)
        page.crop(bbox).to_image(resolution=resolution).save(str(out_png))

    return FigureCrop(task=task, page=page_number, bbox=bbox, png=out_png, warnings=warnings)
