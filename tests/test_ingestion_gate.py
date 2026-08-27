"""M2 gate: one real arkusz, ingested end to end through the job system.

Skips unless the real source files and the tools (pandoc, LibreOffice, poppler)
are all present — it is a full-stack check, not a unit test.
"""

import shutil
from pathlib import Path

import pytest

from tests.conftest import needs_pandoc, needs_soffice
from zaspro.db.models import Job, JobStatus, JobType
from zaspro.ingestion.report import build_report
from zaspro.jobs import Worker, enqueue
from zaspro.seeding.sources import seed_sources

RAW = Path(__file__).resolve().parents[1] / "sources" / "raw"
ARKUSZ = "MMAP-P0-660-A-2605-arkusz.docx"
MARKING = "MMAP-P0-100-2605-zasady.pdf"

pytestmark = [
    needs_pandoc,
    needs_soffice,
    pytest.mark.skipif(shutil.which("pdftotext") is None, reason="poppler not installed"),
    pytest.mark.skipif(
        not (RAW / ARKUSZ).is_file() or not (RAW / MARKING).is_file(),
        reason="real CKE source files not present",
    ),
]


def test_real_arkusz_ingests_end_to_end(db):
    import zaspro.ingestion.handlers  # noqa: F401 - register handlers

    seed_sources(db)
    db.commit()

    enqueue(db, JobType.INGEST_DOCUMENT, {
        "source_file_ref": ARKUSZ, "marking_scheme_file_ref": MARKING,
    })
    db.commit()

    processed = Worker().drain()
    assert processed == 8  # 1 INGEST + 7 RENDER_VECTOR_FIGURE
    # (Zadanie 32's lone stray line is recorded as a non-figure in
    #  sources/figure_overrides.yaml, so it is not one of the 7)

    db.expire_all()
    jobs = db.query(Job).all()
    assert all(j.status == JobStatus.SUCCEEDED for j in jobs), [
        (j.job_type.value, j.status.value) for j in jobs
    ]

    ingest = next(j for j in jobs if j.job_type == JobType.INGEST_DOCUMENT)
    rep = build_report(db, ingest.output["source_document_id"])

    # counts and points match the marking scheme exactly
    assert rep.leaf_tasks == 37
    assert rep.points_total == 50
    # 41 = 4 parents (12, 13, 24, 33) + 37 leaf tasks
    assert rep.exercises == 41 and rep.parents == 4
    assert rep.chunks == 41
    # 7 distinct drawing regions, all rendered; 11 exercises need one
    # (7 own + 4 subtasks of 12 and 13 that inherit); none incomplete.
    assert rep.figure_regions_expected == 7
    assert rep.figure_regions_rendered == 7
    assert rep.figure_bearing_exercises == 11
    assert rep.incomplete == []
    assert rep.figures_ok and rep.complete
