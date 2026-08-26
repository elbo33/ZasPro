from pathlib import Path

import pytest

from zaspro.extraction.boilerplate import strip_boilerplate
from zaspro.extraction.segment import leaf_points, segment_arkusz

FIX = Path(__file__).parent / "fixtures" / "mini_arkusz.tex"


def _chunks():
    body, _ = strip_boilerplate(FIX.read_text(encoding="utf-8"))
    return segment_arkusz(body, source_document="mini_arkusz.tex")


def test_counts_and_parent_subtask_case():
    chunks = _chunks()
    by_num = {c.exercise_number: c for c in chunks}

    # 1, 2, 3(parent), 3.1, 3.2, 4  ->  6 chunks, 1 parent, 5 pointed leaves
    assert len(chunks) == 6
    assert [c.exercise_number for c in chunks] == ["1", "2", "3", "3.1", "3.2", "4"]

    parent = by_num["3"]
    assert parent.is_parent is True
    assert parent.points_available is None
    assert "f(x) = 2x" in parent.statement_latex_raw

    for sub in ("3.1", "3.2"):
        assert by_num[sub].is_parent is False
        assert by_num[sub].parent_number == "3"
        # stem attached at read time, verbatim from the parent
        assert by_num[sub].stem_latex_raw == parent.statement_latex_raw

    assert by_num["3.1"].points_available == 1
    assert by_num["3.2"].points_available == 3


def test_point_marker_accepts_ascii_and_en_dash():
    chunks = {c.exercise_number: c for c in _chunks()}
    assert chunks["1"].points_available == 1  # (0--1)
    assert chunks["4"].points_available == 1  # (0–1) real en dash


def test_leaf_points_excludes_parents():
    lp = leaf_points(_chunks())
    assert "3" not in lp
    assert lp == {"1": 1, "2": 2, "3.1": 1, "3.2": 3, "4": 1}
    assert sum(lp.values()) == 8


def test_media_ref_captured_on_owning_task():
    chunks = {c.exercise_number: c for c in _chunks()}
    assert chunks["3"].media_refs == ["image7.png"]
    assert chunks["1"].media_refs == []


def test_confidence_is_null_for_every_chunk():
    assert all(c.confidence is None for c in _chunks())


def test_expected_figure_count_and_incompleteness():
    body, _ = strip_boilerplate(FIX.read_text(encoding="utf-8"))
    # Zadanie 3 is a parent with a figure; 3.1/3.2 inherit it via the stem.
    chunks = {
        c.exercise_number: c
        for c in segment_arkusz(
            body, source_document="mini", expected_figures={"3": 1}
        )
    }
    assert chunks["3"].expected_figure_count == 1
    assert chunks["3.1"].expected_figure_count == 1  # inherited
    assert chunks["3.2"].expected_figure_count == 1  # inherited
    assert chunks["1"].expected_figure_count == 0

    # media_refs come from the LaTeX; the fixture's \includegraphics for
    # Zadanie 3 is a real extracted asset, so 3 itself is complete...
    assert chunks["3"].media_refs == ["image7.png"]
    assert chunks["3"].figures_incomplete is False
    # ...but the subtasks inherit the expectation without an asset of their own.
    assert chunks["3.1"].figures_incomplete is True

    # A task expecting a figure with nothing extracted is incomplete.
    lonely = segment_arkusz(
        "Zadanie 8. (0--1)\n\nGeometria.\n", source_document="x",
        expected_figures={"8": 1},
    )[0]
    assert lonely.figures_incomplete is True


def test_non_monotonic_numbering_raises():
    body = (
        "Zadanie 1. (0--1)\n\nfoo\n\n"
        "Zadanie 3. (0--1)\n\nbar\n"  # gap: 1 -> 3
    )
    with pytest.raises(ValueError, match="non-monotonic"):
        segment_arkusz(body, source_document="x")


def test_parent_with_points_is_rejected_by_model():
    # A "parent" line that carries a point marker is simply a simple task.
    body = "Zadanie 5. (0--2)\n\nsolo task\n"
    chunks = segment_arkusz(body, source_document="x")
    assert chunks[0].is_parent is False
    assert chunks[0].points_available == 2
