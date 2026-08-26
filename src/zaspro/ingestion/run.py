"""Ingest one arkusz end to end via the job system.

    uv run python -m zaspro.ingestion.run \
        MMAP-P0-660-A-2605-arkusz.docx MMAP-P0-100-2605-zasady.pdf

Enqueues INGEST_DOCUMENT, drains the worker (which also runs the
RENDER_VECTOR_FIGURE jobs it spawns), then prints the completeness report.
"""

from __future__ import annotations

import sys

from sqlalchemy import select

import zaspro.ingestion.handlers  # noqa: F401 - registers job handlers
from zaspro.db.base import session_scope
from zaspro.db.models import Job, JobStatus, JobType
from zaspro.ingestion.report import build_report
from zaspro.jobs import Worker, enqueue

DEFAULT_ARKUSZ = "MMAP-P0-660-A-2605-arkusz.docx"
DEFAULT_MARKING = "MMAP-P0-100-2605-zasady.pdf"


def run(arkusz: str = DEFAULT_ARKUSZ, marking: str = DEFAULT_MARKING) -> int:
    with session_scope() as s:
        job = enqueue(
            s,
            JobType.INGEST_DOCUMENT,
            {"source_file_ref": arkusz, "marking_scheme_file_ref": marking},
        )
        job_id = job.id

    processed = Worker().drain()

    with session_scope() as s:
        ingest = s.get(Job, job_id)
        failed = s.scalars(select(Job).where(Job.status == JobStatus.FAILED)).all()
        print(f"jobs processed: {processed}")
        print(f"INGEST_DOCUMENT: {ingest.status.value}  output={ingest.output}")
        if ingest.status is not JobStatus.SUCCEEDED:
            print(f"  error:\n{ingest.error}")
            return 1
        if failed:
            for j in failed:
                print(f"  FAILED {j.job_type.value} #{j.id}: {j.error.splitlines()[-1] if j.error else ''}")

        doc_id = ingest.output["source_document_id"]
        rep = build_report(s, doc_id)
        print()
        print(f"document        : {rep.document}  ({rep.extraction_status})")
        print(f"chunks          : {rep.chunks}")
        print(f"exercises       : {rep.exercises}  ({rep.parents} parents + {rep.leaf_tasks} leaf)")
        print(f"points total    : {rep.points_total}")
        print(f"figures         : {rep.figures_rendered} rendered / {rep.figures_expected_tasks} figure-bearing tasks")
        print(f"incomplete      : {rep.incomplete or 'none'}")
        return 0 if (rep.complete and not failed) else 1


if __name__ == "__main__":
    args = sys.argv[1:]
    sys.exit(run(*args) if args else run())
