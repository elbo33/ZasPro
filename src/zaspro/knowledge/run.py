"""Run knowledge extraction and hand back the review queue.

    uv run python -m zaspro.knowledge.run --topics 5         # deliberate 5-topic yield check
    uv run python -m zaspro.knowledge.run VIII.5 XII.2 ...    # named requirements
    uv run python -m zaspro.knowledge.run --all              # every podstawowy requirement
    uv run python -m zaspro.knowledge.run --all --force      # include already-frozen topics
    uv run python -m zaspro.knowledge.run --all --reset      # wipe M4 state first, extract clean
    uv run python -m zaspro.knowledge.run I.3 I.4 --no-thinking   # extract without adaptive thinking

Each topic is extracted in two agent calls (structure: concepts/formulas/methods,
then pedagogy: examples/objectives/misconceptions) so no single response has to
carry a large topic's whole spec. A call that hits max_tokens fails the job
loudly — a partial spec is never persisted as complete. An intermittent
`<parameter>` pseudo-syntax malformation in the tool call is re-sampled (not
unpacked); the run reports how often it happened.

With no ANTHROPIC_API_KEY this uses `StubKnowledgeAgent`; with a key,
`ClaudeKnowledgeAgent` (`claude-opus-5`). `--all` prints a cost estimate and
asks before it runs; afterwards it prints the queue depth — one KNOWLEDGE_SPEC
review card per topic — so you know what you are committing to review.

Exit codes: 0 ok, 1 a job failed, 2 bad args / nothing to do / declined.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import func, select

import zaspro.ingestion.handlers  # noqa: F401 - register handlers
import zaspro.knowledge.extract  # noqa: F401 - register EXTRACT_KNOWLEDGE
import zaspro.mapping.handler  # noqa: F401 - register MAP_CHUNK
from zaspro.db.base import session_scope
from zaspro.db.models import (
    ExerciseTopic, Job, JobStatus, JobType, KnowledgeFlag, Misconception,
    MisconceptionSource, ReviewItem, ReviewItemType, ReviewStatus, Topic,
    TopicLevel, TopicRole,
)
from zaspro.jobs import Worker, enqueue
from zaspro.knowledge.agent import ClaudeKnowledgeAgent, KnowledgeRequest, get_agent
from zaspro.knowledge.aggregate import rebuild_exercise_topics, topic_chunk_counts
from zaspro.knowledge.export import is_frozen
from zaspro.knowledge.extract import topic_exercises

OPUS5_IN = 5.0   # $/MTok
OPUS5_OUT = 25.0
_MAX_OUT = 32000


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


def _all_podstawowy(session) -> list[tuple[str, int, str]]:
    rows = session.execute(
        select(Topic.official_requirement_code, Topic.id).where(
            Topic.level == TopicLevel.PODSTAWOWY,
            Topic.official_requirement_code.is_not(None),
        )
    ).all()
    return sorted(((c, tid, "all") for c, tid in rows), key=lambda t: t[0])


def _estimate(session, picks: list[tuple[str, int, str]]) -> tuple[int, int, float, float]:
    """(est_input_tok, est_output_tok, low_usd, high_usd) for a real-agent run.
    Input from the assembled prompt (chars/4); output from the observed shape —
    ~8k floor rising with exercise count, capped at max_tokens."""
    agent = get_agent()
    est_in = est_out = 0
    for _code, tid, _b in picks:
        pairs = topic_exercises(session, tid)
        topic = session.get(Topic, tid)
        req = KnowledgeRequest(
            topic_code=topic.official_requirement_code or str(tid),
            topic_name=topic.name,
            requirement_text=topic.statement_latex or topic.description,
            exercises=[ctx for _, ctx in pairs],
        )
        # TWO calls per topic (structure + pedagogy): the exercises block is
        # resent for each, so input roughly doubles; output total is similar to
        # a single call (~the same items, split across two responses).
        body = agent._user_block(req) if hasattr(agent, "_user_block") else ""
        est_in += 2 * (1600 + len(body) // 4)
        est_out += min(2 * _MAX_OUT, 9000 + 350 * len(pairs))
    lo = (est_in * OPUS5_IN + est_out * 0.7 * OPUS5_OUT) / 1e6
    hi = (est_in * OPUS5_IN + est_out * 1.1 * OPUS5_OUT) / 1e6
    return est_in, est_out, lo, hi


def _snapshot_before_reset(session, out_dir: Path) -> int:
    """Dump every extracted topic's knowledge rows to JSON before `--reset`
    deletes them, so a mistaken reset is recoverable. Returns topic count."""
    from zaspro.db.models import (
        Concept, Example, Formula, KnowledgeExtraction, KnowledgeFlag,
        LearningObjective, Method, Misconception,
    )

    tids = list(session.scalars(select(KnowledgeExtraction.topic_id)))
    if not tids:
        return 0
    out_dir.mkdir(parents=True, exist_ok=True)
    kinds = [("concepts", Concept), ("formulas", Formula), ("methods", Method),
             ("examples", Example), ("objectives", LearningObjective),
             ("misconceptions", Misconception), ("flags", KnowledgeFlag)]
    for tid in tids:
        topic = session.get(Topic, tid)
        code = (topic.official_requirement_code if topic else None) or str(tid)
        data: dict = {"topic_code": code, "topic_id": tid, "items": {}}
        for name, model in kinds:
            rows = session.scalars(select(model).where(model.topic_id == tid)).all()
            data["items"][name] = [
                {c.name: getattr(r, c.name) for c in model.__table__.columns}
                for r in rows
            ]
        (out_dir / f"{code}.json").write_text(
            json.dumps(data, ensure_ascii=False, indent=1, default=str), encoding="utf-8"
        )
    return len(tids)


def _reset_all(session) -> dict:
    """Wipe every M4 knowledge row and its review cards, and clear dead
    EXTRACT_KNOWLEDGE jobs. All of it is derived — regenerable from the
    mappings + a fresh run. Used by `--reset` for a clean `--all`. Every topic
    is snapshotted to m4/reset_backups/<ts>/ first."""
    from zaspro.db.models import (
        Concept, Example, Formula, Job, JobStatus, KnowledgeExtraction,
        KnowledgeFlag, LearningObjective, Method, Misconception, ReviewDecision,
    )

    counts: dict[str, int] = {}
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = Path("m4/reset_backups") / stamp
    counts["snapshotted_topics"] = _snapshot_before_reset(session, backup)
    if counts["snapshotted_topics"]:
        print(f"  snapshot: {counts['snapshotted_topics']} topics -> {backup}/")
    ri_ids = list(session.scalars(
        select(ReviewItem.id).where(ReviewItem.item_type == ReviewItemType.KNOWLEDGE_SPEC)
    ))
    if ri_ids:
        session.query(ReviewDecision).filter(
            ReviewDecision.review_item_id.in_(ri_ids)
        ).delete(synchronize_session=False)
        session.query(ReviewItem).filter(
            ReviewItem.id.in_(ri_ids)
        ).delete(synchronize_session=False)
    counts["review_cards"] = len(ri_ids)
    for model in (Example, Concept, Formula, Method, LearningObjective,
                  Misconception, KnowledgeFlag, KnowledgeExtraction):
        counts[model.__tablename__] = session.query(model).delete(synchronize_session=False)
    counts["dead_jobs"] = session.query(Job).filter(
        Job.job_type == JobType.EXTRACT_KNOWLEDGE,
        Job.status.in_([JobStatus.FAILED, JobStatus.RUNNING, JobStatus.PENDING]),
    ).delete(synchronize_session=False)
    session.flush()
    return counts


def _queue_depth(session) -> dict:
    open_specs = session.scalar(
        select(func.count()).select_from(ReviewItem).where(
            ReviewItem.item_type == ReviewItemType.KNOWLEDGE_SPEC,
            ReviewItem.status == ReviewStatus.OPEN,
        )
    ) or 0
    open_total = session.scalar(
        select(func.count()).select_from(ReviewItem).where(
            ReviewItem.status == ReviewStatus.OPEN
        )
    ) or 0
    flagged_mc = session.scalar(
        select(func.count()).select_from(Misconception).where(
            Misconception.source_kind.in_(
                (MisconceptionSource.AGENT_INFERENCE, MisconceptionSource.UNSOURCED)
            )
        )
    ) or 0
    open_flags = session.scalar(
        select(func.count()).select_from(KnowledgeFlag).where(
            KnowledgeFlag.resolved.is_(False)
        )
    ) or 0
    return {
        "open_knowledge_cards": open_specs,
        "open_review_items_total": open_total,
        "flagged_misconceptions": flagged_mc,
        "unresolved_knowledge_flags": open_flags,
    }


def run(topic_codes: list[str] | None, *, n: int = 5, all_topics: bool = False,
        force: bool = False, assume_yes: bool = False, reset: bool = False,
        no_thinking: bool = False) -> int:
    agent = get_agent()
    real = isinstance(agent, ClaudeKnowledgeAgent)
    if real and no_thinking:
        from zaspro.knowledge.agent import set_agent
        agent = ClaudeKnowledgeAgent(thinking=False)
        set_agent(agent)  # the job handler picks this up via get_agent()
    print(f"agent: {type(agent).__name__} (model={agent.model!r}"
          f"{', thinking=off' if real and no_thinking else ''})")
    if real:
        try:
            print(f"preflight: API reachable, model={agent.preflight()}")
        except Exception as e:  # noqa: BLE001
            print(f"ERROR: Claude preflight failed ({type(e).__name__}): {e}")
            return 2

    with session_scope() as s:
        if reset:
            depth = _queue_depth(s)
            print(f"\n--reset: {depth['open_knowledge_cards']} knowledge cards, "
                  f"{depth['flagged_misconceptions']} flagged misconceptions and all "
                  f"knowledge rows will be DELETED (they are derived, regenerable).")
            if not assume_yes and sys.stdin.isatty():
                if input("wipe M4 knowledge state? [y/N] ").strip().lower() not in ("y", "yes"):
                    print("declined.")
                    return 2
            c = _reset_all(s)
            print(f"  cleared: {c}")

        r = rebuild_exercise_topics(s)  # keep aggregation current with the mappings
        print(f"exercise_topics rebuilt: {r.primary_rows} primary + {r.secondary_rows} "
              f"secondary rows, {r.skipped_unsettled} skipped (unsettled)")

        if all_topics:
            picks = _all_podstawowy(s)
        elif topic_codes:
            rows = s.execute(
                select(Topic.official_requirement_code, Topic.id).where(
                    Topic.official_requirement_code.in_(topic_codes)
                )
            ).all()
            picks = [(code, tid, "explicit") for code, tid in rows]
        else:
            picks = pick_calibration_topics(s, n)

        frozen = [(c, t, b) for (c, t, b) in picks if is_frozen(c)]
        if frozen and not force:
            picks = [p for p in picks if p not in frozen]
            print(f"\nskipping {len(frozen)} frozen (already exported) topic(s): "
                  f"{', '.join(c for c, _, _ in frozen)}")
            print("  pass --force to re-extract them (you then re-review + re-export)")

        if not picks:
            print("nothing to extract")
            return 2

        verbose = len(picks) <= 8
        print(f"\n{len(picks)} topic(s) to extract:")
        for code, tid, bucket in (picks if verbose else picks[:0]):
            n_touch = s.scalar(select(func.count()).select_from(ExerciseTopic).where(
                ExerciseTopic.topic_id == tid))
            n_prim = s.scalar(select(func.count()).select_from(ExerciseTopic).where(
                ExerciseTopic.topic_id == tid, ExerciseTopic.role == TopicRole.PRIMARY))
            print(f"  {code:8} {bucket:36} exercises: {n_touch} touch / {n_prim} primary")

        if real:
            ein, eout, lo, hi = _estimate(s, picks)
            print(f"\nestimated cost (claude-opus-5, $5/MTok in, $25/MTok out):")
            print(f"  ~{ein:,} input tok + ~{eout:,} output tok  ->  ${lo:,.2f}–${hi:,.2f}")
            print("  (output is the driver; the run prints the real figure after)")
            if not assume_yes and sys.stdin.isatty():
                if input("\nproceed? [y/N] ").strip().lower() not in ("y", "yes"):
                    print("declined.")
                    return 2

        hwm = s.scalar(select(func.max(Job.id))) or 0
        for _code, tid, _b in picks:
            payload = {"topic_id": tid}
            if force:
                payload["force"] = True
            enqueue(s, JobType.EXTRACT_KNOWLEDGE, payload)

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
        malformed = 0
        malformed_topics: list[str] = []
        timings: list[tuple[str, float, int]] = []  # (code, elapsed_s, out_tok)
        print("\n" + "=" * 72)
        for status, out in rows:
            if status is JobStatus.FAILED or not out:
                failed += 1
                print(f"  FAILED extraction: {out}")
                continue
            u = out.get("usage") or {}
            ti += u.get("in", 0); to += u.get("out", 0); tcr += u.get("cache_read", 0)
            mr = out.get("malformed_retries", 0)
            if mr:
                malformed += mr
                malformed_topics.append(f"{out['topic_code']}×{mr}")
            el = out.get("elapsed_s") or 0.0
            ot = u.get("out", 0)
            timings.append((out["topic_code"], el, ot))
            if verbose:
                print(f"\n### {out['topic_code']}   ({out['exercises']} exercises)  "
                      f"[{el:.0f}s, {ot:,} out tok]")
                print(f"  concepts {out['concepts']}  formulas {out['formulas']}  "
                      f"methods {out['methods']}  examples {out['examples']}  "
                      f"objectives {out['objectives']}  flags {out['flags']}")
                print(f"  misconceptions: {out['misconceptions']}  "
                      f"(sources: {out['misconception_sources'] or '—'})")
                for d in out["misconception_detail"]:
                    frm = ", ".join(d["from_exercises"]) or "none"
                    dis = f"  dystraktor {d['distractor']}" if d.get("distractor") else ""
                    print(f"    - [{d['source_kind']}] {d['name']}{dis}")
                    print(f"        from Zadanie {frm}  ::  {d['evidence']}")
            else:
                print(f"  {out['topic_code']:8} c{out['concepts']:>2} f{out['formulas']:>2} "
                      f"m{out['methods']:>2} e{out['examples']:>2} o{out['objectives']:>2} "
                      f"mc{out['misconceptions']:>2}  "
                      f"flag {out['flags'] + out.get('flagged_misconceptions', 0):>2}  "
                      f"{el:>5.0f}s / {ot / 1000:.1f}k out")
            for k, v in (out["misconception_sources"] or {}).items():
                src_total[k] = src_total.get(k, 0) + v

        print("\n" + "=" * 72)
        if malformed:
            print(f"malformed tool calls re-sampled: {malformed} across "
                  f"{len(malformed_topics)} topic(s) [{', '.join(malformed_topics)}] "
                  f"— <parameter> pseudo-syntax; raw responses in m4/knowledge_debug/")
        if timings:
            slow = sorted(timings, key=lambda t: -t[1])[:3]
            total_s = sum(t[1] for t in timings)
            print(f"elapsed: {total_s:.0f}s total, slowest "
                  + ", ".join(f"{c} {s:.0f}s ({o:,} out)" for c, s, o in slow))
            near = [c for c, s, _ in timings if s >= 480]
            if near:
                print(f"  WARNING: {len(near)} topic(s) over 8 min "
                      f"({', '.join(near)}) — approaching the 10-min ceiling; "
                      f"streaming keeps them running but the spread is real")
        tot_mc = sum(src_total.values())
        print(f"misconceptions total: {tot_mc}   by source: {src_total or '—'}")
        real_src = (src_total.get("MARKING_SCHEME", 0) + src_total.get("INFORMATOR", 0)
                    + src_total.get("DISTRACTOR_INFERENCE", 0))
        inferred = src_total.get("AGENT_INFERENCE", 0) + src_total.get("UNSOURCED", 0)
        if tot_mc:
            print(f"  from a real source (marking scheme / informator / distractor): "
                  f"{real_src} / {tot_mc}")
            print(f"  agent inference or unsourced (flagged for review): {inferred} / {tot_mc}")
        if real and (ti or to):
            cost = ti / 1e6 * 5 + tcr / 1e6 * 0.5 + to / 1e6 * 25
            print(f"tokens {ti:,} in / {tcr:,} cache-read / {to:,} out  ->  ${cost:,.2f} "
                  "(published claude-opus-5)")

        if failed:
            print(f"\n{failed} extraction(s) FAILED (truncation or API error) — "
                  f"not persisted. Re-run just those topics by code.")

        depth = _queue_depth(s)
        print("\nreview queue (whole database, not just this run):")
        print(f"  {depth['open_knowledge_cards']} open KNOWLEDGE_SPEC cards (one per extracted topic)")
        print(f"  {depth['open_review_items_total']} open review items in total")
        print(f"  {depth['flagged_misconceptions']} flagged misconceptions "
              f"(AGENT_INFERENCE / UNSOURCED) across all extracted topics")
        print(f"  {depth['unresolved_knowledge_flags']} unresolved knowledge flags")
        print("\nReview in the dashboard (Knowledge tab), then export approved topics:")
        print("  uv run python -m zaspro.knowledge.export --all")
    return 1 if failed else 0


if __name__ == "__main__":
    args = sys.argv[1:]
    all_topics = "--all" in args
    force = "--force" in args
    reset = "--reset" in args
    no_thinking = "--no-thinking" in args
    assume_yes = "--yes" in args or "-y" in args
    n = 5
    codes = [a for a in args if not a.startswith("-")]
    if "--topics" in args:
        v = args[args.index("--topics") + 1]
        n = int(v)
        if v in codes:
            codes.remove(v)
    sys.exit(run(codes or None, n=n, all_topics=all_topics, force=force,
                 assume_yes=assume_yes, reset=reset, no_thinking=no_thinking))
