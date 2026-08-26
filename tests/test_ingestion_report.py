"""A lost figure leaves its exercise visibly incomplete, never silently empty
(the M0.4 finding). Unit-level checks on build_report; the full path is in
test_ingestion_incomplete_e2e.py."""

from zaspro.db.models import (
    Exercise,
    ExerciseFigure,
    ExerciseOrigin,
    Figure,
    LicenceStatus,
    RenderStatus,
    Source,
    SourceDocument,
    SourceFormat,
    SourceType,
)
from zaspro.db.models import ExtractionStatus
from zaspro.ingestion.report import build_report


def _doc(db) -> SourceDocument:
    src = Source(
        title="t", publisher="t", source_type=SourceType.EXAM,
        licence_status=LicenceStatus.CKE_UNSPECIFIED, verbatim_ok=False,
        url="x", file_ref="t.docx",
    )
    db.add(src)
    db.flush()
    doc = SourceDocument(
        source_id=src.id, file_ref="t.docx", extraction_status=ExtractionStatus.VALIDATED
    )
    db.add(doc)
    db.flush()
    return doc


def _ex(db, doc, number, *, own=0, expected=0, points=1):
    e = Exercise(
        source_document_id=doc.id, exercise_number=number, statement=number,
        origin=ExerciseOrigin.OFFICIAL, points_available=points,
        own_figure_count=own, expected_figure_count=expected,
    )
    db.add(e)
    db.flush()
    return e


def test_expected_figure_with_no_render_is_reported_incomplete(db):
    doc = _doc(db)
    _ex(db, doc, "1", own=0, expected=0)          # fine
    _ex(db, doc, "2", own=1, expected=1)          # region expected, nothing rendered
    e3 = _ex(db, doc, "3", own=1, expected=1)     # region expected, rendered + linked

    fig = Figure(
        source_document_id=doc.id, source_format=SourceFormat.WORD_SHAPE,
        render_status=RenderStatus.COMPLETE, image_ref="figures/3.png",
    )
    db.add(fig)
    db.flush()
    db.add(ExerciseFigure(exercise_id=e3.id, figure_id=fig.id))
    db.flush()

    rep = build_report(db, doc.id)
    assert rep.incomplete == ["2"]
    assert rep.figure_regions_expected == 2
    assert rep.figure_regions_rendered == 1
    assert rep.figure_bearing_exercises == 2
    assert rep.figures_ok is False
    assert rep.complete is False


def test_inherited_subtask_figure_is_a_bearing_exercise_not_a_region(db):
    doc = _doc(db)
    parent = _ex(db, doc, "12", own=1, expected=1, points=None)
    sub = _ex(db, doc, "12.1", own=0, expected=1)  # inherits 12's figure
    sub.parent_exercise_id = parent.id

    fig = Figure(
        source_document_id=doc.id, source_format=SourceFormat.WORD_SHAPE,
        render_status=RenderStatus.COMPLETE, image_ref="figures/12.png",
    )
    db.add(fig)
    db.flush()
    db.add_all([
        ExerciseFigure(exercise_id=parent.id, figure_id=fig.id),
        ExerciseFigure(exercise_id=sub.id, figure_id=fig.id),
    ])
    db.flush()

    rep = build_report(db, doc.id)
    assert rep.figure_regions_expected == 1       # one drawing region
    assert rep.figure_regions_rendered == 1
    assert rep.figure_bearing_exercises == 2      # 12 and 12.1 both need it
    assert rep.incomplete == []
    assert rep.figures_ok is True                 # 1 == 1 and nothing incomplete


def test_a_failed_render_row_still_counts_as_incomplete(db):
    doc = _doc(db)
    e = _ex(db, doc, "5", own=1, expected=1)
    fig = Figure(
        source_document_id=doc.id, source_format=SourceFormat.WORD_SHAPE,
        render_status=RenderStatus.FAILED, image_ref=None,
    )
    db.add(fig)
    db.flush()
    db.add(ExerciseFigure(exercise_id=e.id, figure_id=fig.id))
    db.flush()

    rep = build_report(db, doc.id)
    assert rep.incomplete == ["5"]            # linked, but not COMPLETE
    assert rep.figure_regions_rendered == 0   # COMPLETE only
