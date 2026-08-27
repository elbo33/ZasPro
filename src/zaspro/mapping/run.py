"""Map an ingested document's chunks to the curriculum via the job system.

    uv run python -m zaspro.mapping.run MMAP-P0-660-A-2605-arkusz.docx
    uv run python -m zaspro.mapping.run MMAP-P0-660-A-2605-arkusz.docx --review-all
    uv run python -m zaspro.mapping.run MMAP-P0-660-A-2605-arkusz.docx --remap
    uv run python -m zaspro.mapping.run MMAP-P0-660-A-2605-arkusz.docx --threshold 0.9

With no ANTHROPIC_API_KEY set this uses the offline `StubMappingAgent`, so the
whole M3 path is runnable without the network; with a key it uses
`ClaudeMappingAgent` (`claude-opus-5`). Enqueues one MAP_CHUNK per selected
chunk, drains the worker, then prints the queue breakdown.

`--review-all` forces every mapping into the review queue regardless of
confidence (threshold 1.01) — the calibration pass.
`--remap` re-runs chunks that already have a mapping, dropping the old mapping
and its review item first. Use it to re-map a paper with a different agent
(stub -> Claude). Without it, already-mapped chunks are skipped and — if that
leaves nothing to do — the command fails rather than reporting a no-op.

Exit codes: 0 success, 1 a job failed, 2 nothing to do / bad arguments.
"""

from __future__ import annotations

import sys

from sqlalchemy import func, select

import zaspro.ingestion.handlers  # noqa: F401 - register handlers
import zaspro.mapping.handler  # noqa: F401 - register MAP_CHUNK
from zaspro.db.base import session_scope
from zaspro.db.models import ChunkMapping, Job, JobStatus, SourceChunk, SourceDocument
from zaspro.jobs import Worker
from zaspro.mapping import AUTO_APPROVE_THRESHOLD, ClaudeMappingAgent, default_agent, map_document
from zaspro.review import queue_stats


def _describe_agent(agent) -> str:
    return f"{type(agent).__name__} (name={agent.name!r}, model={agent.model!r})"


def run(
    doc_ref: str,
    threshold: float = AUTO_APPROVE_THRESHOLD,
    *,
    remap: bool = False,
) -> int:
    agent = default_agent()
    print(f"agent: {_describe_agent(agent)}")

    with session_scope() as s:
        doc = s.scalars(
            select(SourceDocument).where(SourceDocument.file_ref == doc_ref)
        ).one_or_none()
        if doc is None:
            print(f"ERROR: no source_document with file_ref={doc_ref!r}")
            return 2

        total = s.scalar(
            select(func.count()).select_from(SourceChunk).where(
                SourceChunk.source_document_id == doc.id
            )
        ) or 0
        if total == 0:
            print(
                f"ERROR: {doc_ref} has 0 source_chunks — it has not been ingested. "
                "Run the ingestion first."
            )
            return 2

        # how many chunks would be selected, before spending an API call
        to_map = total if remap else s.scalar(
            select(func.count())
            .select_from(SourceChunk)
            .outerjoin(ChunkMapping, ChunkMapping.source_chunk_id == SourceChunk.id)
            .where(
                SourceChunk.source_document_id == doc.id,
                ChunkMapping.id.is_(None),
            )
        ) or 0
        if to_map == 0:
            print(
                f"ERROR: nothing to map — all {total} chunks of {doc_ref} already "
                "have a mapping. Re-run with --remap to replace them "
                "(e.g. to map with the Claude agent after a stub run)."
            )
            return 2

        # cheap local checks passed; now one tiny real call so a bad key /
        # model / network fails before anything is enqueued (and so "did it
        # actually hit the API?" is answered up front)
        if isinstance(agent, ClaudeMappingAgent):
            try:
                echoed = agent.preflight()
            except Exception as e:  # noqa: BLE001 - surface the real reason
                print(f"ERROR: Claude preflight call failed ({type(e).__name__}): {e}")
                return 2
            print(f"preflight: API reachable, model={echoed}")

        summary = map_document(s, doc.id, agent, threshold=threshold, remap=remap)
        print(
            f"threshold: {threshold}  remap: {remap}  "
            f"chunks: {summary['chunks']}  selected: {summary['selected']}  "
            f"enqueued: {summary['jobs']} MAP_CHUNK jobs"
        )
        assert summary["jobs"] > 0, "to_map was > 0 but nothing enqueued"

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
    args = sys.argv[1:]
    if not args or args[0].startswith("-"):
        print(__doc__)
        sys.exit(2)
    doc_ref = args[0]
    thr = AUTO_APPROVE_THRESHOLD
    if "--review-all" in args:
        thr = 1.01
    if "--threshold" in args:
        thr = float(args[args.index("--threshold") + 1])
    sys.exit(run(doc_ref, thr, remap="--remap" in args))
