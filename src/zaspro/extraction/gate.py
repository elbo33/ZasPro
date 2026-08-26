"""The M0.2 hard gate: segmented arkusz vs its zasady oceniania.

Counts and point values must match exactly, else the milestone fails.
"""

from __future__ import annotations

from .models import ExerciseChunk, MarkingSchemeTask, SegmentationGateResult
from .segment import leaf_points


def cross_validate(
    chunks: list[ExerciseChunk],
    marking_tasks: list[MarkingSchemeTask],
    *,
    source_document: str,
    marking_scheme: str,
    marking_scheme_is_deterministic: bool,
) -> SegmentationGateResult:
    arkusz = leaf_points(chunks)
    marking = {t.exercise_number: t.points_available for t in marking_tasks}

    missing_in_arkusz = sorted(set(marking) - set(arkusz), key=_sort_key)
    missing_in_marking = sorted(set(arkusz) - set(marking), key=_sort_key)
    point_mismatches = [
        (num, arkusz[num], marking[num])
        for num in sorted(set(arkusz) & set(marking), key=_sort_key)
        if arkusz[num] != marking[num]
    ]

    return SegmentationGateResult(
        source_document=source_document,
        marking_scheme=marking_scheme,
        marking_scheme_is_deterministic=marking_scheme_is_deterministic,
        arkusz_task_count=len(arkusz),
        marking_task_count=len(marking),
        arkusz_points_total=sum(arkusz.values()),
        marking_points_total=sum(marking.values()),
        missing_in_arkusz=missing_in_arkusz,
        missing_in_marking=missing_in_marking,
        point_mismatches=point_mismatches,
    )


def _sort_key(num: str) -> tuple[int, int]:
    top, _, sub = num.partition(".")
    return int(top), int(sub) if sub else 0
