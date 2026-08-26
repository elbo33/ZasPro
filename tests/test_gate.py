from zaspro.extraction.gate import cross_validate
from zaspro.extraction.models import ExerciseChunk, MarkingSchemeTask


def _chunk(num, pts, *, parent=False, parent_num=None):
    return ExerciseChunk(
        source_document="x",
        order_index=0,
        exercise_number=num,
        parent_number=parent_num,
        is_parent=parent,
        points_available=pts,
        statement_latex_raw="...",
    )


def _kw(**over):
    base = dict(
        source_document="a.docx",
        marking_scheme="z.pdf",
        marking_scheme_is_deterministic=False,
    )
    base.update(over)
    return base


def test_exact_match_passes():
    chunks = [
        _chunk("1", 1),
        _chunk("2", 2),
        _chunk("3", None, parent=True),
        _chunk("3.1", 1, parent_num="3"),
        _chunk("3.2", 3, parent_num="3"),
    ]
    marking = [
        MarkingSchemeTask(exercise_number="1", points_available=1),
        MarkingSchemeTask(exercise_number="2", points_available=2),
        MarkingSchemeTask(exercise_number="3.1", points_available=1),
        MarkingSchemeTask(exercise_number="3.2", points_available=3),
    ]
    res = cross_validate(chunks, marking, **_kw())
    assert res.passed
    assert res.arkusz_task_count == 4  # parent excluded
    assert res.arkusz_points_total == 7 == res.marking_points_total


def test_missing_task_fails():
    chunks = [_chunk("1", 1)]
    marking = [
        MarkingSchemeTask(exercise_number="1", points_available=1),
        MarkingSchemeTask(exercise_number="2", points_available=1),
    ]
    res = cross_validate(chunks, marking, **_kw())
    assert not res.passed
    assert res.missing_in_arkusz == ["2"]


def test_point_mismatch_fails():
    chunks = [_chunk("1", 1), _chunk("2", 1)]
    marking = [
        MarkingSchemeTask(exercise_number="1", points_available=1),
        MarkingSchemeTask(exercise_number="2", points_available=2),
    ]
    res = cross_validate(chunks, marking, **_kw())
    assert not res.passed
    assert res.point_mismatches == [("2", 1, 2)]
