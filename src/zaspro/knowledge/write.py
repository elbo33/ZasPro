"""Write a knowledge spec for each teaching section and hand back the review queue.

    uv run python -m zaspro.knowledge.write --all
    uv run python -m zaspro.knowledge.write funkcja-liniowa ciag-arytmetyczny
    uv run python -m zaspro.knowledge.write --all --force   # include frozen sections

One agent call per section (ADR 0012). No exercises, no retry logic: if a
section's call fails, the job fails, the run prints it and moves on. Every
section leaves one KNOWLEDGE_SPEC review card; approve it in the dashboard, then
`zaspro.knowledge.export` freezes it to git.

Exit codes: 0 ok, 1 a section failed, 2 bad args / nothing to do / declined.
"""

from __future__ import annotations

import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

import zaspro.ingestion.handlers  # noqa: F401 - register handlers
from zaspro.db.base import session_scope
from zaspro.db.models import (
    Concept, Example, Formula, Job, JobStatus, JobType, LearningObjective,
    Method, Misconception, ReviewItem, ReviewItemType, ReviewStatus, Section,
    SectionSpec, Topic,
)
from zaspro.jobs import Worker, enqueue, register
from zaspro.knowledge.agent import (
    ClaudeSectionAgent, KnowledgeAgent, KnowledgeError, RequirementCtx,
    SectionRequest, get_agent,
)
from zaspro.knowledge.export import is_frozen

OPUS5_IN, OPUS5_OUT = 5.0, 25.0  # $/MTok

_ITEM_MODELS = [
    ("concepts", Concept), ("formulas", Formula), ("methods", Method),
    ("examples", Example), ("objectives", LearningObjective),
    ("misconceptions", Misconception),
]


class KnowledgeFrozen(RuntimeError):
    """The section has a committed export file (ADR 0012). Re-writing needs an
    explicit force flag; the committed file is never overwritten silently."""


@dataclass
class WriteResult:
    slug: str
    concepts: int = 0
    formulas: int = 0
    methods: int = 0
    examples: int = 0
    objectives: int = 0
    misconceptions: int = 0
    review_item_id: int | None = None


def _clear_section(session: Session, section_id: int) -> None:
    for _name, model in _ITEM_MODELS:
        session.query(model).filter_by(section_id=section_id).delete()
    session.flush()


def _upsert_review_item(session: Session, section: Section) -> ReviewItem:
    ri = session.scalars(
        select(ReviewItem).where(
            ReviewItem.item_type == ReviewItemType.KNOWLEDGE_SPEC,
            ReviewItem.ref_table == "sections",
            ReviewItem.ref_id == section.id,
        )
    ).one_or_none()
    title = f"Section spec: {section.slug} — {section.name[:80]}"
    if ri is None:
        ri = ReviewItem(
            item_type=ReviewItemType.KNOWLEDGE_SPEC, ref_table="sections",
            ref_id=section.id, status=ReviewStatus.OPEN, risk=0.5,
            confidence=None, title=title,
        )
        session.add(ri)
    else:
        ri.status = ReviewStatus.OPEN
        ri.resolved_at = None
        ri.title = title
    session.flush()
    return ri


def _upsert_spec(session: Session, section_id: int, agent: KnowledgeAgent,
                 review_item_id: int) -> None:
    row = session.scalars(
        select(SectionSpec).where(SectionSpec.section_id == section_id)
    ).one_or_none()
    fields = dict(
        agent_name=getattr(agent, "name", type(agent).__name__),
        model=getattr(agent, "model", None),
        prompt_version=getattr(agent, "prompt_version", "?"),
        written_at=datetime.now(timezone.utc),
        review_item_id=review_item_id,
        approved_at=None, approved_by=None, exported_at=None, export_path=None,
    )
    if row is None:
        session.add(SectionSpec(section_id=section_id, **fields))
    else:
        for k, v in fields.items():
            setattr(row, k, v)
    session.flush()


def _request(session: Session, section: Section) -> SectionRequest:
    reqs = []
    for sr in section.requirements:
        t = session.get(Topic, sr.topic_id)
        reqs.append(RequirementCtx(
            code=t.official_requirement_code or str(sr.topic_id),
            text=t.name,
        ))
    reqs.sort(key=lambda r: r.code)
    return SectionRequest(
        slug=section.slug, name=section.name, scope=section.scope, requirements=reqs
    )


def write_section(session: Session, section_id: int, agent: KnowledgeAgent | None = None,
                  *, force: bool = False) -> WriteResult:
    agent = agent or get_agent()
    section = session.get(Section, section_id)
    if section is None:
        raise KnowledgeError(f"section {section_id} not found")
    if is_frozen(section.slug) and not force:
        raise KnowledgeFrozen(
            f"{section.slug}: knowledge/sections/{section.slug}.yaml exists — frozen. "
            f"Pass force=True to re-write (you must then re-review and re-export)."
        )

    spec = agent.write(_request(session, section))

    _clear_section(session, section_id)
    res = WriteResult(section.slug)

    for i, c in enumerate(spec.concepts):
        session.add(Concept(
            section_id=section_id, order_index=i, name=c.name[:255],
            description=c.definition, explanation=c.explanation, difficulty=c.difficulty,
        ))
        res.concepts += 1
    for i, f in enumerate(spec.formulas):
        session.add(Formula(
            section_id=section_id, order_index=i, name=f.name[:255],
            latex_raw=f.latex, conditions=f.conditions, description=f.note,
        ))
        res.formulas += 1
    for i, m in enumerate(spec.methods):
        session.add(Method(
            section_id=section_id, order_index=i, name=m.name[:255],
            when_to_use=m.when_to_use, steps=m.steps,
        ))
        res.methods += 1
    for i, e in enumerate(spec.examples):
        session.add(Example(
            section_id=section_id, order_index=i, statement=e.statement,
            worked_solution=e.worked_solution, difficulty=e.difficulty,
        ))
        res.examples += 1
    for i, o in enumerate(spec.objectives):
        session.add(LearningObjective(
            section_id=section_id, order_index=i, statement=o.statement,
            bloom_level=o.bloom_level,
        ))
        res.objectives += 1
    for i, mc in enumerate(spec.misconceptions):
        session.add(Misconception(
            section_id=section_id, order_index=i, name=mc.name[:255],
            incorrect_reasoning=mc.incorrect_reasoning,
            correct_reasoning=mc.correct_reasoning, severity=mc.severity,
        ))
        res.misconceptions += 1

    session.flush()
    ri = _upsert_review_item(session, section)
    res.review_item_id = ri.id
    _upsert_spec(session, section_id, agent, ri.id)
    return res


@register(JobType.EXTRACT_KNOWLEDGE)
def handle_write_section(session: Session, job: Job) -> dict:
    section_id = job.input.get("section_id")
    if section_id is None:
        raise KnowledgeError("job has no section_id (stale pre-0013 job)")
    agent = get_agent()
    t0 = time.monotonic()
    res = write_section(session, section_id, agent, force=bool(job.input.get("force")))
    out = {
        "elapsed_s": round(time.monotonic() - t0, 1),
        "slug": res.slug,
        "concepts": res.concepts, "formulas": res.formulas, "methods": res.methods,
        "examples": res.examples, "objectives": res.objectives,
        "misconceptions": res.misconceptions,
        "review_item_id": res.review_item_id,
    }
    if getattr(agent, "last_usage", None):
        out["usage"] = agent.last_usage
    return out


# --------------------------------------------------------------------------- #

def _cleanup_stale(session: Session) -> None:
    """Clear leftovers that only add noise: topic-scoped KNOWLEDGE_SPEC review
    cards (pre-0013), and any not-succeeded EXTRACT_KNOWLEDGE job — a fresh run
    supersedes them all."""
    from zaspro.db.models import ReviewDecision

    stale_ri = list(session.scalars(
        select(ReviewItem.id).where(
            ReviewItem.item_type == ReviewItemType.KNOWLEDGE_SPEC,
            ReviewItem.ref_table != "sections",
        )
    ))
    if stale_ri:
        session.query(ReviewDecision).filter(
            ReviewDecision.review_item_id.in_(stale_ri)
        ).delete(synchronize_session=False)
        session.query(ReviewItem).filter(
            ReviewItem.id.in_(stale_ri)
        ).delete(synchronize_session=False)
    session.query(Job).filter(
        Job.job_type == JobType.EXTRACT_KNOWLEDGE,
        Job.status.in_([JobStatus.PENDING, JobStatus.RUNNING, JobStatus.FAILED]),
    ).delete(synchronize_session=False)
    session.flush()


def _targets(session: Session, slugs: list[str] | None) -> list[Section]:
    stmt = select(Section).order_by(Section.order_index)
    if slugs:
        stmt = stmt.where(Section.slug.in_(slugs))
    return list(session.scalars(stmt))


def run(slugs: list[str] | None, *, all_sections: bool = False, force: bool = False,
        assume_yes: bool = False) -> int:
    agent = get_agent()
    real = isinstance(agent, ClaudeSectionAgent)
    print(f"agent: {type(agent).__name__} (model={agent.model!r})")
    if real:
        try:
            print(f"preflight: API reachable, model={agent.preflight()}")
        except Exception as e:  # noqa: BLE001
            print(f"ERROR: Claude preflight failed ({type(e).__name__}): {e}")
            return 2

    with session_scope() as s:
        if not all_sections and not slugs:
            print("usage: python -m zaspro.knowledge.write --all | <slug>...")
            return 2
        _cleanup_stale(s)
        sections = _targets(s, slugs)
        if not sections:
            print("no matching sections")
            return 2

        frozen = [x for x in sections if is_frozen(x.slug)]
        if frozen and not force:
            sections = [x for x in sections if x not in frozen]
            print(f"skipping {len(frozen)} frozen section(s): "
                  f"{', '.join(x.slug for x in frozen)} (pass --force)")
        if not sections:
            print("nothing to write")
            return 2

        print(f"\n{len(sections)} section(s) to write:")
        for x in sections:
            codes = ", ".join(sorted(
                s.get(Topic, sr.topic_id).official_requirement_code
                for sr in x.requirements
            ))
            print(f"  {x.slug:44} [{codes}]")

        if real:
            # rough: ~1k input, ~18k output per section (full textbook spec)
            n = len(sections)
            lo = (n * 1000 * OPUS5_IN + n * 14000 * OPUS5_OUT) / 1e6
            hi = (n * 1500 * OPUS5_IN + n * 24000 * OPUS5_OUT) / 1e6
            print(f"\nestimated cost (claude-opus-5): ${lo:,.2f}–${hi:,.2f} "
                  f"for {n} section(s)")
            if not assume_yes and sys.stdin.isatty():
                if input("proceed? [y/N] ").strip().lower() not in ("y", "yes"):
                    print("declined.")
                    return 2

        hwm = s.scalar(select(func.max(Job.id))) or 0
        for x in sections:
            payload = {"section_id": x.id}
            if force:
                payload["force"] = True
            enqueue(s, JobType.EXTRACT_KNOWLEDGE, payload)

    Worker().drain()

    failed = 0
    ti = to = tcr = 0
    with session_scope() as s:
        rows = s.execute(
            select(Job.status, Job.output, Job.error).where(
                Job.job_type == JobType.EXTRACT_KNOWLEDGE, Job.id > hwm
            )
        ).all()
        print("\n" + "=" * 72)
        for status, out, err in rows:
            if status is JobStatus.FAILED or not out:
                failed += 1
                last = (err or "").strip().splitlines()[-1] if err else "?"
                print(f"  FAILED: {last}")
                continue
            u = out.get("usage") or {}
            ti += u.get("in", 0); to += u.get("out", 0); tcr += u.get("cache_read", 0)
            print(f"  {out['slug']:44} c{out['concepts']:>2} f{out['formulas']:>2} "
                  f"m{out['methods']:>2} e{out['examples']:>2} o{out['objectives']:>2} "
                  f"mc{out['misconceptions']:>2}   {out.get('elapsed_s', 0):>5.0f}s")

        print("\n" + "=" * 72)
        if failed:
            print(f"{failed} section(s) FAILED — not persisted. Re-run them by slug.")
        if real and (ti or to):
            cost = ti / 1e6 * OPUS5_IN + tcr / 1e6 * 0.5 + to / 1e6 * OPUS5_OUT
            print(f"tokens {ti:,} in / {tcr:,} cache-read / {to:,} out  ->  ${cost:,.2f}")

        open_cards = s.scalar(
            select(func.count()).select_from(ReviewItem).where(
                ReviewItem.item_type == ReviewItemType.KNOWLEDGE_SPEC,
                ReviewItem.status == ReviewStatus.OPEN,
            )
        ) or 0
        print(f"\nreview queue: {open_cards} open section cards (dashboard -> Knowledge).")
        print("Approve, then: uv run python -m zaspro.knowledge.export --all")
    return 1 if failed else 0


if __name__ == "__main__":
    args = sys.argv[1:]
    all_sections = "--all" in args
    force = "--force" in args
    assume_yes = "--yes" in args or "-y" in args
    slugs = [a for a in args if not a.startswith("-")]
    sys.exit(run(slugs or None, all_sections=all_sections, force=force, assume_yes=assume_yes))
