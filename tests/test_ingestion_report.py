"""A lost figure leaves its exercise visibly incomplete, never silently empty
(the M0.4 finding — the easiest thing in M2 to lose)."""

from zaspro.db.models import (
    Exercise,
    ExerciseFigure,
    ExerciseOrigin,
    Figure,
    RenderStatus,
    Source,
    SourceDocument,
    SourceFormat,
    LicenceStatus,
    SourceType,
)
from zaspro.ingestion.report import build_report


def _doc(db) -> SourceDocument:
    src = Source(
        title="t", publisher="t", source_type=SourceType.EXAM,
        licence_status=LicenceStatus.CKE_UNSPECIFIED, verbatim_ok=False,
        url="x", file_ref="t.docx",
    )
    db.add(src)
    db.flush()
    doc = SourceDocument(source_id=src.id, file_ref="t.docx")
    db.add(doc)
    db.flush()
    return doc


def _ex(db, doc, number, *, expect_fig, points=1):
    e = Exercise(
        source_document_id=doc.id, exercise_number=number, statement=number,
        origin=ExerciseOrigin.OFFICIAL, points_available=points,
        expected_figure_count=expect_fig,
    )
    db.add(e)
    db.flush()
    return e


def test_expected_figure_with_no_render_is_reported_incomplete(db):
    doc = _doc(db)
    _ex(db, doc, "1", expect_fig=0)          # fine
    e2 = _ex(db, doc, "2", expect_fig=1)     # figure expected, none linked
    e3 = _ex(db, doc, "3", expect_fig=1)     # figure expected, rendered + linked

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
    assert rep.complete is False
    assert rep.figures_expected_tasks == 2
    assert rep.figures_rendered == 1


def test_a_failed_render_still_counts_as_incomplete(db):
    doc = _doc(db)
    e = _ex(db, doc, "5", expect_fig=1)
    fig = Figure(
        source_document_id=doc.id, source_format=SourceFormat.WORD_SHAPE,
        render_status=RenderStatus.FAILED, image_ref=None,
    )
    db.add(fig)
    db.flush()
    db.add(ExerciseFigure(exercise_id=e.id, figure_id=fig.id))
    db.flush()

    rep = build_report(db, doc.id)
    assert rep.incomplete == ["5"]  # linked, but not COMPLETE
