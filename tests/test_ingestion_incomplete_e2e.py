"""End to end: a document whose figure cannot be rendered must surface as
incomplete through the whole path — job system included, not just the report
function. A detection mechanism that has never fired is not yet evidence.

The synthetic arkusz's Zadanie 3 carries an empty `<w:drawing>`: it is counted
(`own_figure_count = 1`) but LibreOffice renders no ink for it, so the crop
finds no vector primitives and RENDER_VECTOR_FIGURE genuinely fails.
"""

import pytest

from tests.conftest import needs_pandoc, needs_soffice
from zaspro.db.models import (
    Exercise,
    Job,
    JobStatus,
    JobType,
    LicenceStatus,
    Source,
    SourceType,
)
from zaspro.ingestion.report import build_report
from zaspro.jobs import Worker, enqueue

pytestmark = [needs_pandoc, needs_soffice]

MARKING = [
    {"exercise_number": "1", "points_available": 1},
    {"exercise_number": "2.1", "points_available": 2},
    {"exercise_number": "2.2", "points_available": 1},
    {"exercise_number": "3", "points_available": 2},
]


def test_unrenderable_figure_surfaces_as_incomplete(db, mini_docx):
    import zaspro.ingestion.handlers  # noqa: F401 - register handlers

    db.add(Source(
        title="synthetic arkusz", publisher="test", source_type=SourceType.EXAM,
        licence_status=LicenceStatus.CKE_UNSPECIFIED, verbatim_ok=False,
        url="x", file_ref=mini_docx.name,
    ))
    enqueue(db, JobType.INGEST_DOCUMENT, {
        "source_file_ref": str(mini_docx),
        "marking_tasks": MARKING,
    })
    db.commit()

    Worker().drain()
    db.expire_all()

    jobs = db.query(Job).all()
    ingest = next(j for j in jobs if j.job_type == JobType.INGEST_DOCUMENT)
    renders = [j for j in jobs if j.job_type == JobType.RENDER_VECTOR_FIGURE]

    # the deterministic part succeeded: gate passed, exercises persisted
    assert ingest.status == JobStatus.SUCCEEDED
    assert ingest.output["gate"] == "pass"

    # the one figure job ran, retried, and failed
    assert len(renders) == 1
    r = renders[0]
    assert r.input["exercise_number"] == "3"
    assert r.status == JobStatus.FAILED
    assert r.attempts == r.max_attempts
    assert "no vector primitives" in r.error

    # and Zadanie 3 is visibly incomplete, not silently empty
    doc_id = ingest.output["source_document_id"]
    rep = build_report(db, doc_id)
    assert rep.figure_regions_expected == 1
    assert rep.figure_regions_rendered == 0
    assert rep.figure_bearing_exercises == 1
    assert rep.incomplete == ["3"]
    assert rep.figures_ok is False
    assert rep.complete is False

    ex3 = db.query(Exercise).filter_by(exercise_number="3").one()
    assert ex3.expected_figure_count == 1
    assert ex3.figures == []  # nothing linked
