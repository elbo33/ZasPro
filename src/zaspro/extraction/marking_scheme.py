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
from functools import lru_cache
from pathlib import Path

from .models import MarkingSchemeTask

_OVERRIDES = (
    Path(__file__).resolve().parents[3] / "sources" / "marking_scheme_overrides.yaml"
)
_SESSION_IN_NAME = re.compile(r"-(\d{4})-zasady\.pdf$")

_DASH = r"[‐-―\-]+"
# The period after the task number is optional: pre-2024 multi-variant zasady
# PDFs write subtasks as "Zadanie 13.1 (0–1)" (no trailing period), the 2024+
# format writes "Zadanie 13.1. (0–1)". Both are the same task.
_TASK_LINE = re.compile(
    r"^Zadanie\s+(?P<num>\d+(?:\.\d+)?)\.?\s*"
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


@lru_cache(maxsize=1)
def _load_overrides() -> dict:
    if not _OVERRIDES.is_file():
        return {}
    import yaml

    return yaml.safe_load(_OVERRIDES.read_text(encoding="utf-8")) or {}


def apply_overrides(
    tasks: list[MarkingSchemeTask], session_code: str
) -> list[MarkingSchemeTask]:
    """Merge in hand-entered corrections for one session (see
    `sources/marking_scheme_overrides.yaml`). This is the *only* way a task the
    PDF failed to make machine-readable gets a point value — never inference."""

    entry = _load_overrides().get(session_code)
    if not entry:
        return tasks

    by_num = {t.exercise_number: t for t in tasks}
    for add in entry.get("add_tasks", []):
        num = str(add["number"])
        if num in by_num:
            continue  # the parser found it after all; leave it alone
        by_num[num] = MarkingSchemeTask(
            exercise_number=num, points_available=int(add["points"])
        )
    for fix in entry.get("set_points", []):
        num = str(fix["number"])
        if num in by_num:
            by_num[num] = MarkingSchemeTask(
                exercise_number=num, points_available=int(fix["points"])
            )
    return sorted(
        by_num.values(),
        key=lambda t: [int(p) for p in t.exercise_number.split(".")],
    )


def parse_marking_scheme(pdf: Path) -> list[MarkingSchemeTask]:
    pdf = Path(pdf)
    tasks = parse_marking_scheme_text(pdf_to_text(pdf))
    m = _SESSION_IN_NAME.search(pdf.name)
    if m:
        tasks = apply_overrides(tasks, m.group(1))
    return tasks


def marking_points(tasks: list[MarkingSchemeTask]) -> dict[str, int]:
    return {t.exercise_number: t.points_available for t in tasks}
