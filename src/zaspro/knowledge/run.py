"""Run knowledge extraction on a few topics and report the misconception yield.

    uv run python -m zaspro.knowledge.run --topics 5
    uv run python -m zaspro.knowledge.run VIII.5 XII.2 ...

With no ANTHROPIC_API_KEY this uses `StubKnowledgeAgent`; with a key,
`ClaudeKnowledgeAgent` (`claude-opus-5`). `--topics 5` picks a **deliberate**
spread — two requirements well covered under the touch definition, two mid, one
of the requirements with no primary exercise coverage — so the report shows
whether misconception yield tracks material volume or is uniformly thin.

Reports, per topic: concept/formula/method/example/objective counts, and every
misconception with its `source_kind` (MARKING_SCHEME / INFORMATOR /
AGENT_INFERENCE / UNSOURCED), the exercises it cites, and the evidence snippet.
Then holds. Exit codes: 0 ok, 1 a job failed, 2 bad args / nothing mapped.
"""

from __future__ import annotations

import sys

from sqlalchemy import func, select

import zaspro.ingestion.handlers  # noqa: F401 - register handlers
import zaspro.knowledge.extract  # noqa: F401 - register EXTRACT_KNOWLEDGE
import zaspro.mapping.handler  # noqa: F401 - register MAP_CHUNK
from zaspro.db.base import session_scope
from zaspro.db.models import ExerciseTopic, Job, JobStatus, JobType, Topic, TopicLevel, TopicRole
from zaspro.jobs import Worker, enqueue
from zaspro.knowledge.agent import ClaudeKnowledgeAgent, get_agent
from zaspro.knowledge.aggregate import rebuild_exercise_topics, topic_chunk_counts


def pick_calibration_topics(session, n: int = 5) -> list[tuple[str, int, str]]:
    """(code, topic_id, bucket). A deliberate spread, not the first five:
    two requirements well covered under *touch* (and with primary coverage too),
    two mid, one of the requirements with **no primary** exercise. Deterministic;
    no code picked twice."""
    counts = {c.code: c for c in topic_chunk_counts(session)}
    ids = dict(
        session.execute(
            select(Topic.official_requirement_code, Topic.id).where(
                Topic.level == TopicLevel.PODSTAWOWY,
                Topic.official_requirement_code.is_not(None),
            )
        ).all()
    )
    high = sorted(
        (c for c in counts.values() if c.touch >= 5 and c.primary >= 1),
        key=lambda c: (-c.touch, -c.primary, c.code),
    )
    mid = sorted(
        (c for c in counts.values() if 3 <= c.touch <= 4),
        key=lambda c: (-c.touch, -c.primary, c.code),
    )
    zero = sorted(
        (c for c in counts.values() if c.primary == 0),
        key=lambda c: (-c.touch, c.code),
    )

    picked: list[tuple[str, int, str]] = []
    taken: set[str] = set()
    for bucket, pool, k in (("high-touch", high, 2), ("mid-touch", mid, 2), ("zero-primary", zero, 1)):
        got = 0
        for c in pool:
            if c.code in taken:
                continue
            taken.add(c.code)
            picked.append((c.code, ids[c.code], f"{bucket} (primary {c.primary}, touch {c.touch})"))
            got += 1
            if got == k:
                break
    return picked[:n]


def run(topic_codes: list[str] | None, *, n: int = 5) -> int:
    agent = get_agent()
    real = isinstance(agent, ClaudeKnowledgeAgent)
    print(f"agent: {type(agent).__name__} (model={agent.model!r})")
    if real:
        try:
            print(f"preflight: API reachable, model={agent.preflight()}")
        except Exception as e:  # noqa: BLE001
            print(f"ERROR: Claude preflight failed ({type(e).__name__}): {e}")
            return 2

    with session_scope() as s:
        r = rebuild_exercise_topics(s)  # keep aggregation current with the mappings
        print(f"exercise_topics rebuilt: {r.primary_rows} primary + {r.secondary_rows} "
              f"secondary rows, {r.skipped_unsettled} skipped (unsettled)")
        if topic_codes:
            rows = s.execute(
                select(Topic.official_requirement_code, Topic.id).where(
                    Topic.official_requirement_code.in_(topic_codes)
                )
            ).all()
            picks = [(code, tid, "explicit") for code, tid in rows]
        else:
            picks = pick_calibration_topics(s, n)
        if not picks:
            print("no topics to extract")
            return 2

        print("\ntopics:")
        for code, _tid, bucket in picks:
            n_touch = s.scalar(
                select(func.count()).select_from(ExerciseTopic).where(
                    ExerciseTopic.topic_id == _tid
                )
            )
            n_prim = s.scalar(
                select(func.count()).select_from(ExerciseTopic).where(
                    ExerciseTopic.topic_id == _tid, ExerciseTopic.role == TopicRole.PRIMARY
                )
            )
            print(f"  {code:8} {bucket:40} exercises: {n_touch} touch / {n_prim} primary")

        hwm = s.scalar(select(func.max(Job.id))) or 0
        for _code, tid, _b in picks:
            enqueue(s, JobType.EXTRACT_KNOWLEDGE, {"topic_id": tid})

    Worker().drain()

    with session_scope() as s:
        rows = s.execute(
            select(Job.status, Job.output).where(
                Job.job_type == JobType.EXTRACT_KNOWLEDGE, Job.id > hwm
            )
        ).all()

    failed = 0
    src_total: dict[str, int] = {}
    ti = to = tcr = 0
    print("\n" + "=" * 72)
    for status, out in rows:
        if status is JobStatus.FAILED or not out:
            failed += 1
            print(f"  FAILED extraction: {out}")
            continue
        u = out.get("usage") or {}
        ti += u.get("in", 0); to += u.get("out", 0); tcr += u.get("cache_read", 0)
        print(f"\n### {out['topic_code']}   ({out['exercises']} exercises)")
        print(f"  concepts {out['concepts']}  formulas {out['formulas']}  "
              f"methods {out['methods']}  examples {out['examples']}  "
              f"objectives {out['objectives']}  flags {out['flags']}")
        print(f"  misconceptions: {out['misconceptions']}  "
              f"(sources: {out['misconception_sources'] or '—'})")
        for d in out["misconception_detail"]:
            frm = ", ".join(d["from_exercises"]) or "none"
            print(f"    - [{d['source_kind']}] {d['name']}")
            print(f"        from Zadanie {frm}  ::  {d['evidence']}")
        for k, v in (out["misconception_sources"] or {}).items():
            src_total[k] = src_total.get(k, 0) + v

    print("\n" + "=" * 72)
    tot_mc = sum(src_total.values())
    print(f"misconceptions total: {tot_mc}   by source: {src_total or '—'}")
    inferred = src_total.get("AGENT_INFERENCE", 0) + src_total.get("UNSOURCED", 0)
    if tot_mc:
        print(f"  from a real source (marking scheme / informator): "
              f"{tot_mc - inferred} / {tot_mc}")
        print(f"  agent inference or unsourced: {inferred} / {tot_mc}")
    if real and (ti or to):
        cost = ti / 1e6 * 5 + tcr / 1e6 * 0.5 + to / 1e6 * 25
        print(f"tokens {ti:,} in / {tcr:,} cache-read / {to:,} out  ->  est. ${cost:,.2f} "
              "(published claude-opus-5)")
    print("\nHold here — read the yield before extracting the rest.")
    return 1 if failed else 0


if __name__ == "__main__":
    args = sys.argv[1:]
    n = 5
    codes = [a for a in args if not a.startswith("-")]
    if "--topics" in args:
        v = args[args.index("--topics") + 1]
        n = int(v)
        if v in codes:
            codes.remove(v)
    sys.exit(run(codes or None, n=n))
