"""Track A ingestion on synthetic input — no real source material (SPEC §18)."""

import pytest

from tests.conftest import needs_pandoc
from zaspro.db.models import (
    ContentType,
    Exercise,
    ExtractionMethod,
    Source,
    SourceChunk,
    SourceType,
    LicenceStatus,
)
from zaspro.extraction.models import MarkingSchemeTask
from zaspro.ingestion.persist import persist_ingestion
from zaspro.ingestion.pipeline import (
    GateFailed,
    IngestionResult,
    segment_document,
    validate_against_marking,
)


@needs_pandoc
def test_segment_document_finds_tasks_and_the_drawing(mini_docx, tmp_path):
    seg = segment_document(mini_docx, tmp_path / "work")
    nums = [c.exercise_number for c in seg.chunks]
    assert nums == ["1", "2", "2.1", "2.2", "3"]

    by = {c.exercise_number: c for c in seg.chunks}
    assert by["2"].is_parent and by["2"].points_available is None
    assert by["2.1"].parent_number == "2" and by["2.1"].points_available == 2
    assert seg.figures_by_task == {"3": 1}
    # the parent's stem is attached to each child at read time
    assert "funkcja f" in (by["2.1"].stem_latex_raw or "")


@needs_pandoc
def test_gate_passes_and_fails(mini_docx, tmp_path):
    seg = segment_document(mini_docx, tmp_path / "work")
    good = [
        MarkingSchemeTask(exercise_number=n, points_available=p)
        for n, p in [("1", 1), ("2.1", 2), ("2.2", 1), ("3", 2)]
    ]
    gate = validate_against_marking(seg, good, marking_scheme="synthetic")
    assert gate.passed and gate.arkusz_points_total == 6

    with pytest.raises(GateFailed):
        validate_against_marking(
            seg,
            good + [MarkingSchemeTask(exercise_number="4", points_available=1)],
            marking_scheme="synthetic",
        )


@needs_pandoc
def test_persist_writes_chunks_exercises_and_provenance(db, mini_docx, tmp_path):
    db.add(Source(
        title="synthetic", publisher="t", source_type=SourceType.EXAM,
        licence_status=LicenceStatus.CKE_UNSPECIFIED, verbatim_ok=False,
        url="x", file_ref=mini_docx.name,
    ))
    db.flush()

    seg = segment_document(mini_docx, tmp_path / "work")
    result = IngestionResult(
        source_file=seg.source_file, conversion=seg.conversion, body=seg.body,
        chunks=seg.chunks, figures_by_task=seg.figures_by_task,
        figure_chrome=seg.figure_chrome, figure_total=seg.figure_total, gate=None,
    )
    doc = persist_ingestion(db, result)
    db.flush()

    chunks = db.query(SourceChunk).filter_by(source_document_id=doc.id).all()
    assert len(chunks) == 5
    assert all(c.confidence is None for c in chunks)  # deterministic — the M0 finding
    assert all(c.extraction_method == ExtractionMethod.pandoc_omml for c in chunks)
    assert all(c.content_type == ContentType.EXERCISE for c in chunks)
    assert [c.order_index for c in chunks] == [0, 1, 2, 3, 4]  # provenance: order kept

    exercises = {e.exercise_number: e for e in db.query(Exercise).filter_by(source_document_id=doc.id)}
    assert exercises["2.1"].parent.exercise_number == "2"
    assert exercises["2.1"].points_available == 2
    assert exercises["3"].expected_figure_count == 1
    assert exercises["3"].full_statement  # stem+own; here no parent so == own
    assert exercises["2.1"].full_statement.startswith(exercises["2"].statement[:20])
