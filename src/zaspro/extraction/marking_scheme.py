"""Parse the zasady oceniania into an independent task/points enumeration.

The marking scheme lists every task once as ``Zadanie N[.M]. (0-M)`` and is the
validation oracle for segmentation (SPEC decision 5, M0.2).

The M0 corpus has no ``_660.docx`` marking-scheme sibling (CKE publishes
``-zasady`` only as PDF; see docs/sources.md A3), so this reads the ``100`` PDF
via ``pdftotext -layout``. That is the M0.1 exception recorded in
m0/corpus_split.md; it is the one non-deterministic input to the gate.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from .models import MarkingSchemeTask

_DASH = r"[‐-―\-]+"
_TASK_LINE = re.compile(
    r"^Zadanie\s+(?P<num>\d+(?:\.\d+)?)\.\s*"
    rf"\((?P<lo>\d+)\s*{_DASH}\s*(?P<hi>\d+)\)",
    re.MULTILINE,
)


class PdftotextNotFound(RuntimeError):
    pass


def pdf_to_text(pdf: Path) -> str:
    try:
        proc = subprocess.run(
            ["pdftotext", "-layout", str(pdf), "-"],
            capture_output=True,
            text=True,
            check=True,
        )
    except FileNotFoundError as exc:  # pragma: no cover - environment guard
        raise PdftotextNotFound("pdftotext (poppler) is not on PATH") from exc
    return proc.stdout


def parse_marking_scheme_text(text: str) -> list[MarkingSchemeTask]:
    tasks: dict[str, int] = {}
    for m in _TASK_LINE.finditer(text):
        num, hi = m.group("num"), int(m.group("hi"))
        if num in tasks and tasks[num] != hi:
            raise ValueError(
                f"marking scheme lists Zadanie {num} with two point values: "
                f"{tasks[num]} and {hi}"
            )
        tasks.setdefault(num, hi)
    if not tasks:
        raise ValueError("no 'Zadanie N. (0-M)' lines found in marking scheme text")
    return [MarkingSchemeTask(exercise_number=n, points_available=p) for n, p in tasks.items()]


def parse_marking_scheme(pdf: Path) -> list[MarkingSchemeTask]:
    return parse_marking_scheme_text(pdf_to_text(Path(pdf)))


def marking_points(tasks: list[MarkingSchemeTask]) -> dict[str, int]:
    return {t.exercise_number: t.points_available for t in tasks}
