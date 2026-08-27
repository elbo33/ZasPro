"""Count expected figures per task from the DOCX body.

Pandoc drops Word-drawn shapes (`<w:drawing>` with no embedded media) silently,
so a geometry task can lose its figure with no trace in the LaTeX. SPEC forbids
that: "An exercise whose source region contained a figure and which has no
linked figure row is a data error, not an acceptable state."

This walks `word/document.xml` in document order, attributes every `<w:drawing>`
to the task whose `Zadanie N[.M].` marker most recently opened, and returns the
count per task. The segmenter puts that number on each chunk as
``expected_figure_count``; a chunk with ``expected_figure_count`` greater than
``len(media_refs)`` is visibly incomplete.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
import zipfile
from functools import lru_cache
from pathlib import Path

_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

_FIGURE_OVERRIDES = (
    Path(__file__).resolve().parents[3] / "sources" / "figure_overrides.yaml"
)
_SESSION_RE = re.compile(r"MMAP-[PR]0-\d{3}-(?:[AB]-)?(\d{4})")


@lru_cache(maxsize=1)
def _load_figure_overrides() -> dict:
    if not _FIGURE_OVERRIDES.is_file():
        return {}
    import yaml

    return yaml.safe_load(_FIGURE_OVERRIDES.read_text(encoding="utf-8")) or {}


def apply_figure_overrides(counts: dict[str, int], source_name: str) -> dict[str, int]:
    """Overlay hand-entered per-task figure-count corrections
    (`sources/figure_overrides.yaml`). Used where a `<w:drawing>` counted by the
    walker is an editing artifact, not a figure — recorded by a human, never
    inferred from geometry."""

    m = _SESSION_RE.search(source_name or "")
    if not m:
        return counts
    entry = _load_figure_overrides().get(m.group(1))
    if not entry:
        return counts
    out = dict(counts)
    for num, ov in entry.items():
        if isinstance(ov, dict) and "expected_figure_count" in ov:
            out[str(num)] = int(ov["expected_figure_count"])
    return out
_MARKER_TEXT = re.compile(
    r"^\s*Zadanie\s+(?P<num>\d+(?:\.\d+)?)\.\s*"
    r"(?:\(\s*\d+\s*[‐-―\-]+\s*\d+\s*\))?\s*$"
)
_END = re.compile(r"^\s*Koniec\s*$")

BOILERPLATE = "__boilerplate__"


def _paragraph_text(p: ET.Element) -> str:
    """Concatenated `<w:t>` text of a paragraph, excluding any `<w:drawing>`
    subtree (a figure's textbox must not be read as the paragraph's text)."""

    out: list[str] = []

    def rec(e: ET.Element) -> None:
        if e.tag == _W + "drawing":
            return
        if e.tag == _W + "t" and e.text:
            out.append(e.text)
        for child in e:
            rec(child)

    for child in p:
        rec(child)
    return "".join(out)


class _Walker:
    def __init__(self) -> None:
        self.counts: dict[str, int] = {}
        self.current = BOILERPLATE
        self._drawing_depth = 0

    def walk(self, elem: ET.Element) -> None:
        tag = elem.tag
        entered_drawing = tag == _W + "drawing"
        if entered_drawing:
            self._drawing_depth += 1
            # current is BOILERPLATE before the first marker and after Koniec,
            # so chrome drawings land there and the totals reconcile.
            self.counts[self.current] = self.counts.get(self.current, 0) + 1
        elif tag == _W + "p" and self._drawing_depth == 0:
            text = _paragraph_text(elem)
            m = _MARKER_TEXT.match(text)
            if m:
                self.current = m.group("num")
                self.counts.setdefault(self.current, 0)
            elif _END.match(text):
                self.current = BOILERPLATE

        for child in elem:
            self.walk(child)

        if entered_drawing:
            self._drawing_depth -= 1


def _document_xml(docx: Path) -> str:
    with zipfile.ZipFile(docx) as zf:
        return zf.read("word/document.xml").decode("utf-8", "replace")


def _attribute(xml_text: str) -> tuple[dict[str, int], int, int]:
    root = ET.fromstring(xml_text)
    w = _Walker()
    w.walk(root)
    total = sum(1 for _ in root.iter(_W + "drawing"))
    boilerplate = w.counts.pop(BOILERPLATE, 0)
    return w.counts, boilerplate, total


def count_drawings_in_xml(xml_text: str) -> dict[str, int]:
    """Per-task `<w:drawing>` counts from a raw ``document.xml`` string."""

    return _attribute(xml_text)[0]


def count_drawings_by_task(docx: Path) -> dict[str, int]:
    """Map every ``Zadanie`` number to the number of `<w:drawing>` in its range.

    Drawings before the first marker or after ``Koniec`` are dropped (they are
    cover / running-header / footer chrome). Every task that opens a marker is
    present in the result, even with a zero count. Hand-entered figure-count
    overrides (``sources/figure_overrides.yaml``) are applied last.
    """

    docx = Path(docx)
    return apply_figure_overrides(_attribute(_document_xml(docx))[0], docx.name)


def drawing_attribution(docx: Path) -> tuple[dict[str, int], int, int]:
    """(per-task counts, boilerplate count, total body drawings) — for reporting.

    ``total`` is the raw physical drawing count; the per-task map has any
    ``figure_overrides.yaml`` corrections applied, so the two need not reconcile
    exactly where an override zeroed a non-figure drawing.
    """

    docx = Path(docx)
    counts, boilerplate, total = _attribute(_document_xml(docx))
    return apply_figure_overrides(counts, docx.name), boilerplate, total
