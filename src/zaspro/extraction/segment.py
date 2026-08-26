"""Segment a boilerplate-stripped arkusz body into ExerciseChunk records.

Confirmed structure (SPEC M0.2, verified against MMAP-P0-660-A-2605):

    Zadanie 7. (0--2)      -> simple task, 2 points
    Zadanie 12.            -> parent, no points, holds the shared stem
    Zadanie 12.1. (0--2)   -> subtask of 12, stem attached at read time

Markers occupy their own line. A point marker is ``(0--M)`` in pandoc output
(``--`` is an en dash); the zasady oceniania uses a real en dash. Both are
accepted here so the same parser serves ``marking_scheme.py``.
"""

from __future__ import annotations

import re

from .models import ExerciseChunk

# 0x2010-0x2015 = hyphen, non-breaking hyphen, figure/en/em dashes; plus ASCII '-'.
_DASH = r"[\u2010-\u2015\-]+"

TASK_MARKER = re.compile(
    r"^Zadanie\s+(?P<num>\d+(?:\.\d+)?)\.[ \t]*"
    rf"(?:\((?P<lo>\d+)\s*{_DASH}\s*(?P<hi>\d+)\))?[ \t]*$",
    re.MULTILINE,
)

_INCLUDEGRAPHICS = re.compile(r"\\includegraphics(?:\[[^\]]*\])?\{(?P<path>[^}]*)\}")


def _media_refs(block: str) -> list[str]:
    refs: list[str] = []
    for m in _INCLUDEGRAPHICS.finditer(block):
        name = m.group("path").rsplit("/", 1)[-1]
        if name and name not in refs:
            refs.append(name)
    return refs


def segment_arkusz(
    body: str,
    source_document: str,
    expected_figures: dict[str, int] | None = None,
) -> list[ExerciseChunk]:
    """Split *body* into chunks.

    *expected_figures* maps ``Zadanie`` number to the count of ``<w:drawing>``
    elements in that task's DOCX range (see ``figures.count_drawings_by_task``).
    It is attached to each chunk as ``expected_figure_count`` so silent figure
    loss is detectable before figure extraction exists (M0.4).
    """

    expected_figures = expected_figures or {}
    markers = list(TASK_MARKER.finditer(body))
    if not markers:
        raise ValueError("no 'Zadanie' markers in body")

    chunks: list[ExerciseChunk] = []
    current_parent_stem: dict[str, str] = {}  # parent number -> stem LaTeX

    for i, m in enumerate(markers):
        start = m.end()
        end = markers[i + 1].start() if i + 1 < len(markers) else len(body)
        text = body[start:end].strip()

        num = m.group("num")
        has_points = m.group("hi") is not None
        is_subtask = "." in num
        parent_number = num.split(".", 1)[0] if is_subtask else None
        is_parent = not is_subtask and not has_points

        stem = None
        if is_parent:
            current_parent_stem[num] = text
        elif is_subtask:
            stem = current_parent_stem.get(parent_number)

        # A subtask carries its parent's stem at read time, so a figure in the
        # parent's range is a figure this subtask needs too.
        own_figs = expected_figures.get(num, 0)
        inherited_figs = expected_figures.get(parent_number, 0) if is_subtask else 0

        chunks.append(
            ExerciseChunk(
                source_document=source_document,
                order_index=i,
                exercise_number=num,
                parent_number=parent_number,
                is_parent=is_parent,
                points_available=int(m.group("hi")) if has_points else None,
                statement_latex_raw=text,
                stem_latex_raw=stem,
                media_refs=_media_refs(text),
                own_figure_count=own_figs,
                expected_figure_count=own_figs + inherited_figs,
            )
        )

    _check_monotonic(chunks)
    return chunks


def _check_monotonic(chunks: list[ExerciseChunk]) -> None:
    """Top-level exercise numbers must increase by 1 with no gaps (SPEC section 12)."""

    seen_top: list[int] = []
    for c in chunks:
        top = int(c.exercise_number.split(".", 1)[0])
        if not seen_top:
            seen_top.append(top)
        elif top == seen_top[-1]:
            continue
        elif top == seen_top[-1] + 1:
            seen_top.append(top)
        else:
            raise ValueError(
                f"non-monotonic exercise numbering: {seen_top[-1]} -> {top}"
            )


def leaf_points(chunks: list[ExerciseChunk]) -> dict[str, int]:
    """Map every pointed leaf task (simple task or subtask) to its point value."""

    return {
        c.exercise_number: c.points_available
        for c in chunks
        if not c.is_parent and c.points_available is not None
    }
