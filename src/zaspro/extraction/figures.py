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
from pathlib import Path

_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
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
    present in the result, even with a zero count.
    """

    return _attribute(_document_xml(Path(docx)))[0]


def drawing_attribution(docx: Path) -> tuple[dict[str, int], int, int]:
    """(per-task counts, boilerplate count, total body drawings) — for reporting."""

    return _attribute(_document_xml(Path(docx)))
