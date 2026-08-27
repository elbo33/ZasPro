"""Map ingested documents' chunks to the curriculum via the job system.

    uv run python -m zaspro.mapping.run MMAP-P0-660-A-2605-arkusz.docx
    uv run python -m zaspro.mapping.run FILE1.docx FILE2.docx ...        # batch
    uv run python -m zaspro.mapping.run FILE.docx --review-all
    uv run python -m zaspro.mapping.run FILE.docx --remap
    uv run python -m zaspro.mapping.run FILE.docx --threshold 0.9

With no ANTHROPIC_API_KEY this uses the offline `StubMappingAgent`; with a key
it uses `ClaudeMappingAgent` (`claude-opus-5`). Enqueues one MAP_CHUNK per
selected chunk, drains the worker, prints per-paper queue depth and — for the
real agent — token usage and an estimated API cost.

`--review-all` forces every mapping into the review queue (threshold 1.01) — the
calibration pass. `--remap` re-runs chunks that already have a mapping, dropping
the old rows and review item first. Without it, already-mapped chunks are
skipped; if that leaves a paper with nothing to do it is reported and skipped.
`--rate-in` / `--rate-out` override the $/1M-token rates for the cost estimate;
the defaults are the published `claude-opus-5` base rates (checked 27 Aug 2026:
$5 input, $25 output, $0.50 cache-read per MTok).

Exit codes: 0 success, 1 a job failed, 2 bad arguments / a paper not ingested.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass

from sqlalchemy import func, select

import zaspro.ingestion.handlers  # noqa: F401 - register handlers
import zaspro.mapping.handler  # noqa: F401 - register MAP_CHUNK
from zaspro.db.base import session_scope
from zaspro.db.models import (
    ChunkMapping,
    Job,
    JobStatus,
    JobType,
    ReviewItem,
    ReviewStatus,
    SourceChunk,
    SourceDocument,
)
from zaspro.jobs import Worker
from zaspro.mapping import AUTO_APPROVE_THRESHOLD, ClaudeMappingAgent, map_document
from zaspro.mapping.handler import get_agent
from zaspro.review import queue_stats


# Published claude-opus-5 base rates, $/1M tokens (checked 27 Aug 2026 against
# platform.claude.com/docs/en/about-claude/pricing). Prompt caching: 5-min
# write = 1.25x base input, cache read = 0.1x base input.
OPUS5_RATE_IN = 5.0
OPUS5_RATE_OUT = 25.0


@dataclass
class PaperResult:
    ref: str
    mapped: int
    queued: int  # review items this paper added
    tok_in: int  # fresh input only
    tok_out: int
    tok_cache_read: int
    tok_cache_write: int
    failed: int


def _describe_agent(agent) -> str:
    return f"{type(agent).__name__} (name={agent.name!r}, model={agent.model!r})"


def _to_map(s, doc_id: int, total: int, remap: bool) -> int:
    if remap:
        return total
    return s.scalar(
        select(func.count())
        .select_from(SourceChunk)
        .outerjoin(
            ChunkMapping,
            (ChunkMapping.source_chunk_id == SourceChunk.id)
            & ChunkMapping.is_primary.is_(True),
        )
        .where(SourceChunk.source_document_id == doc_id, ChunkMapping.id.is_(None))
    ) or 0


def _open_items(s) -> int:
    return s.scalar(
        select(func.count()).select_from(ReviewItem).where(
            ReviewItem.status == ReviewStatus.OPEN
        )
    ) or 0


def run(
    doc_refs: list[str],
    threshold: float = AUTO_APPROVE_THRESHOLD,
    *,
    remap: bool = False,
    rate_in: float = OPUS5_RATE_IN,
    rate_out: float = OPUS5_RATE_OUT,
) -> int:
    agent = get_agent()  # honours zaspro.mapping.set_agent() for offline tests
    print(f"agent: {_describe_agent(agent)}")
    real = isinstance(agent, ClaudeMappingAgent)

    if real:
        try:
            echoed = agent.preflight()
        except Exception as e:  # noqa: BLE001 - surface the real reason
            print(f"ERROR: Claude preflight call failed ({type(e).__name__}): {e}")
            return 2
        print(f"preflight: API reachable, model={echoed}")

    results: list[PaperResult] = []
    for ref in doc_refs:
        with session_scope() as s:
            doc = s.scalars(
                select(SourceDocument).where(SourceDocument.file_ref == ref)
            ).one_or_none()
            if doc is None:
                print(f"ERROR: no source_document with file_ref={ref!r}")
                return 2
            total = s.scalar(
                select(func.count()).select_from(SourceChunk).where(
                    SourceChunk.source_document_id == doc.id
                )
            ) or 0
            if total == 0:
                print(f"ERROR: {ref} has 0 source_chunks — not ingested.")
                return 2
            n = _to_map(s, doc.id, total, remap)
            if n == 0:
                print(f"  {ref}: already mapped, nothing to do (use --remap to replace)")
                continue

            job_hwm = s.scalar(select(func.max(Job.id))) or 0
            open_before = _open_items(s)
            map_document(s, doc.id, agent, threshold=threshold, remap=remap)

        Worker().drain()

        with session_scope() as s:
            rows = s.execute(
                select(Job.status, Job.output).where(
                    Job.job_type == JobType.MAP_CHUNK, Job.id > job_hwm
                )
            ).all()
            tok_in = tok_out = tok_cr = tok_cw = failed = mapped = 0
            for status, out in rows:
                if status is JobStatus.FAILED:
                    failed += 1
                    continue
                mapped += 1
                u = (out or {}).get("usage") or {}
                tok_in += int(u.get("in", 0))
                tok_out += int(u.get("out", 0))
                tok_cr += int(u.get("cache_read", 0))
                tok_cw += int(u.get("cache_write", 0))
            queued = max(0, _open_items(s) - open_before)
            results.append(
                PaperResult(ref, mapped, queued, tok_in, tok_out, tok_cr, tok_cw, failed)
            )
            cache = f", {tok_cr:,} cache-read" if tok_cr else ""
            print(
                f"  {ref}: mapped {mapped}, queued {queued}, failed {failed}, "
                f"tokens {tok_in:,} in{cache} / {tok_out:,} out"
            )

    # totals
    tot_mapped = sum(r.mapped for r in results)
    tot_queued = sum(r.queued for r in results)
    tot_in = sum(r.tok_in for r in results)
    tot_out = sum(r.tok_out for r in results)
    tot_cr = sum(r.tok_cache_read for r in results)
    tot_cw = sum(r.tok_cache_write for r in results)
    tot_failed = sum(r.failed for r in results)

    with session_scope() as s:
        st = queue_stats(s)

    print()
    print(f"papers mapped        : {len(results)}")
    print(f"chunks mapped        : {tot_mapped}  (failed {tot_failed})")
    print(f"review queue depth   : {st.open_total}  (this run added {tot_queued})")
    print(f"  by type            : {st.by_type}")
    print(f"  mappings by status  : {st.mappings_by_status}")
    if real and (tot_in or tot_out or tot_cr):
        cost = (
            tot_in / 1e6 * rate_in
            + tot_cw / 1e6 * (rate_in * 1.25)   # 5-min cache write
            + tot_cr / 1e6 * (rate_in * 0.10)   # cache read
            + tot_out / 1e6 * rate_out
        )
        rate_note = (
            "published claude-opus-5 rate, checked 27 Aug 2026"
            if (rate_in, rate_out) == (OPUS5_RATE_IN, OPUS5_RATE_OUT)
            else "overridden rate"
        )
        print()
        print(
            f"tokens               : {tot_in:,} in  /  {tot_cr:,} cache-read  /  "
            f"{tot_cw:,} cache-write  /  {tot_out:,} out"
        )
        print(
            f"est. API cost        : ${cost:,.2f}  "
            f"(${rate_in:g}/${rate_out:g}/1M in/out; cache 1.25x write, 0.1x read "
            f"— {rate_note})"
        )
        if results:
            print(
                f"  per paper (avg)     : ${cost / len(results):,.4f}  "
                f"(~{tot_mapped // len(results)} chunks)"
            )
    return 1 if tot_failed else 0


if __name__ == "__main__":
    args = sys.argv[1:]
    refs = [a for a in args if not a.startswith("-")]
    # drop the value that follows a value-taking flag
    for flag in ("--threshold", "--rate-in", "--rate-out"):
        if flag in args:
            v = args[args.index(flag) + 1]
            if v in refs:
                refs.remove(v)
    if not refs:
        print(__doc__)
        sys.exit(2)

    thr = 1.01 if "--review-all" in args else AUTO_APPROVE_THRESHOLD
    if "--threshold" in args:
        thr = float(args[args.index("--threshold") + 1])
    ri = float(args[args.index("--rate-in") + 1]) if "--rate-in" in args else OPUS5_RATE_IN
    ro = float(args[args.index("--rate-out") + 1]) if "--rate-out" in args else OPUS5_RATE_OUT
    sys.exit(run(refs, thr, remap="--remap" in args, rate_in=ri, rate_out=ro))
