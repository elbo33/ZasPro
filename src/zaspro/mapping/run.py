"""Map an ingested document's chunks to the curriculum via the job system.

    uv run python -m zaspro.mapping.run MMAP-P0-660-A-2605-arkusz.docx

With no ANTHROPIC_API_KEY set this uses the offline `StubMappingAgent`, so the
whole M3 path is runnable without the network; with a key it uses
`ClaudeMappingAgent` (`claude-opus-5`). Enqueues one MAP_CHUNK per unmapped
chunk, drains the worker, then prints the queue breakdown.
"""

from __future__ import annotations

import sys

import zaspro.ingestion.handlers  # noqa: F401 - register handlers
import zaspro.mapping.handler  # noqa: F401 - register MAP_CHUNK
from zaspro.db.base import session_scope
from zaspro.db.models import Job, JobStatus, SourceDocument
from zaspro.jobs import Worker
from zaspro.mapping import default_agent, map_document
from zaspro.review import queue_stats
from sqlalchemy import select


def run(doc_ref: str) -> int:
    agent = default_agent()
    with session_scope() as s:
        doc = s.scalars(
            select(SourceDocument).where(SourceDocument.file_ref == doc_ref)
        ).one_or_none()
        if doc is None:
            print(f"no source_document with file_ref={doc_ref!r}")
            return 1
        summary = map_document(s, doc.id, agent)
        print(f"agent: {agent.name}  enqueued {summary['jobs']} MAP_CHUNK jobs")

    processed = Worker().drain()

    with session_scope() as s:
        failed = s.scalars(select(Job).where(Job.status == JobStatus.FAILED)).all()
        st = queue_stats(s)
        print(f"jobs processed: {processed}")
        if failed:
            for j in failed:
                last = j.error.splitlines()[-1] if j.error else ""
                print(f"  FAILED {j.job_type.value} #{j.id}: {last}")
        print()
        print(f"mappings by status : {st.mappings_by_status}")
        print(f"review queue depth : {st.open_total}  by type {st.by_type}")
        print(f"unmapped chunks    : {st.unmapped_chunks}")
        print(f"batchable groups   : {st.batchable_groups}")
    return 1 if failed else 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(run(sys.argv[1]))
