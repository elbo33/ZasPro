"""Per-topic knowledge extraction: build the request, call the agent,
business-rule-validate (SPEC §11/§12), persist. `EXTRACT_KNOWLEDGE` job.

Aggregation is over `exercise_topics` — PRIMARY ∪ approved SECONDARY (ADR 0010),
via `Exercise.full_statement` (stem + body), never `SourceChunk.text` alone.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from zaspro.db.models import (
    Concept, Example, Exercise, ExerciseTopic, Formula, Job, JobType,
    KnowledgeExtraction, KnowledgeFlag, FlagKind, LearningObjective, Method,
    Misconception, MisconceptionSource, ReviewItem, ReviewItemType,
    ReviewStatus, SourceChunk, SourceDocument, Topic,
)
from zaspro.jobs import register
from zaspro.knowledge.agent import (
    ExerciseCtx, KnowledgeAgent, KnowledgeError, KnowledgeRequest, get_agent,
)
from zaspro.knowledge.export import is_frozen

_ZAD = re.compile(r"^Zadanie\s+(\d+(?:\.\d+)?)\.?\s*\(0", re.MULTILINE)
_BLOCK_START = re.compile(r"Zasady oceniania")
_BLOCK_END = re.compile(r"Rozwiązanie|Przykład|Komentarz|Schemat|Uwaga")

# A `from_exercises` entry can be a bare "11.1", or natural phrasing the model
# reaches for despite the schema — "Zadanie 11.1", "Zad 11.1 dystraktory B and
# D". Pull every number token out and match it against the topic's real set.
_NUM = re.compile(r"\d+(?:\.\d+)?")
# When `from_exercises` comes back empty, the model has usually still named the
# task in its prose ("widać to w Zadaniu 4…"). Recover it, but only behind a
# "Zad"/"Zadanie" marker so digits inside a formula are not mistaken for refs.
_PROSE_REF = re.compile(r"zad(?:anie|aniu|ania|\.)?\s*(\d+(?:\.\d+)?)", re.I)


class KnowledgeFrozen(KnowledgeError):
    """The topic already has a committed export file (ADR 0011). Re-extraction
    needs an explicit force flag; the committed file is never overwritten
    silently."""


@dataclass
class ExtractResult:
    topic_code: str
    exercises: int
    concepts: int = 0
    formulas: int = 0
    methods: int = 0
    examples: int = 0
    objectives: int = 0
    misconceptions: int = 0
    misconception_sources: dict[str, int] = field(default_factory=dict)
    misconception_detail: list[dict] = field(default_factory=list)
    flags: int = 0
    unsourced_misconceptions: int = 0
    flagged_misconceptions: int = 0  # AGENT_INFERENCE or UNSOURCED — routed to review
    review_item_id: int | None = None


def _marking_blocks(session_code: str | None) -> dict[str, str]:
    """`{task_number: 'Zasady oceniania' text}` for a session, best-effort."""
    if not session_code:
        return {}
    try:
        from zaspro.analysis.exercise_coverage import _zasady_text  # noqa: PLC0415
        text = _zasady_text(session_code)
    except Exception:  # noqa: BLE001 - no zasady, no blocks
        return {}
    marks = list(_ZAD.finditer(text))
    out: dict[str, str] = {}
    for i, m in enumerate(marks):
        seg = text[m.end(): marks[i + 1].start() if i + 1 < len(marks) else len(text)]
        s = _BLOCK_START.search(seg)
        if not s:
            continue
        rest = seg[s.end():]
        e = _BLOCK_END.search(rest)
        out[m.group(1)] = rest[: e.start() if e else 400].strip()[:600]
    return out


def topic_exercises(session: Session, topic_id: int) -> list[tuple[Exercise, ExerciseCtx]]:
    ex_ids = list(
        session.scalars(
            select(ExerciseTopic.exercise_id).where(ExerciseTopic.topic_id == topic_id)
        )
    )
    if not ex_ids:
        return []
    rows = session.scalars(select(Exercise).where(Exercise.id.in_(ex_ids))).all()
    # marking blocks per source document / session
    blocks_by_session: dict[str, dict[str, str]] = {}
    out: list[tuple[Exercise, ExerciseCtx]] = []
    for ex in sorted(rows, key=lambda e: (e.source_document_id or 0, e.exercise_number)):
        sc = None
        if ex.source_document_id is not None:
            doc = session.get(SourceDocument, ex.source_document_id)
            sess = doc.session_code if doc else None
            if sess and sess not in blocks_by_session:
                blocks_by_session[sess] = _marking_blocks(sess)
            sc = blocks_by_session.get(sess, {}).get(ex.exercise_number)
        out.append((ex, ExerciseCtx(
            number=ex.exercise_number,
            text=ex.full_statement,
            latex=ex.full_statement_latex,
            difficulty=ex.difficulty,
            points=ex.points_available,
            marking_scheme=sc,
        )))
    return out


def _clear_topic(session: Session, topic_id: int) -> None:
    for model in (Concept, Formula, Method, Example, Misconception, LearningObjective):
        session.query(model).filter_by(topic_id=topic_id).delete()
    session.query(KnowledgeFlag).filter_by(topic_id=topic_id).delete()
    session.flush()


def _upsert_review_item(session: Session, topic: Topic, *, has_flags: bool) -> ReviewItem:
    """The one KNOWLEDGE_SPEC card per topic (ADR 0011). Reused across
    re-extractions; a resolved card is reopened for a fresh decision."""
    code = topic.official_requirement_code or str(topic.id)
    ri = session.scalars(
        select(ReviewItem).where(
            ReviewItem.item_type == ReviewItemType.KNOWLEDGE_SPEC,
            ReviewItem.ref_table == "topics",
            ReviewItem.ref_id == topic.id,
        )
    ).one_or_none()
    risk = 0.6 if has_flags else 0.4
    title = f"Knowledge spec: {code} — {topic.name[:80]}"
    if ri is None:
        ri = ReviewItem(
            item_type=ReviewItemType.KNOWLEDGE_SPEC, ref_table="topics", ref_id=topic.id,
            status=ReviewStatus.OPEN, risk=risk, confidence=None, title=title,
            topic_id=topic.id,
        )
        session.add(ri)
    else:
        ri.status = ReviewStatus.OPEN
        ri.resolved_at = None
        ri.risk = risk
        ri.title = title
    session.flush()
    return ri


def _upsert_extraction(
    session: Session, topic_id: int, agent: KnowledgeAgent, n_exercises: int,
    review_item_id: int,
) -> None:
    ke = session.scalars(
        select(KnowledgeExtraction).where(KnowledgeExtraction.topic_id == topic_id)
    ).one_or_none()
    now = datetime.now(timezone.utc)
    fields = dict(
        agent_name=getattr(agent, "name", type(agent).__name__),
        model=getattr(agent, "model", None),
        prompt_version=getattr(agent, "prompt_version", "?"),
        exercises=n_exercises,
        extracted_at=now,
        review_item_id=review_item_id,
        approved_at=None, approved_by=None, exported_at=None, export_path=None,
    )
    if ke is None:
        session.add(KnowledgeExtraction(topic_id=topic_id, **fields))
    else:
        for k, v in fields.items():
            setattr(ke, k, v)
    session.flush()


def extract_topic(
    session: Session, topic_id: int, agent: KnowledgeAgent | None = None,
    *, force: bool = False,
) -> ExtractResult:
    agent = agent or get_agent()
    topic = session.get(Topic, topic_id)
    if topic is None:
        raise KnowledgeError(f"topic {topic_id} not found")

    code = topic.official_requirement_code
    if is_frozen(code) and not force:
        raise KnowledgeFrozen(
            f"{code}: knowledge/topics/{code}.yaml exists — this topic is frozen. "
            f"Pass force=True to re-extract (you must then re-review and re-export)."
        )

    pairs = topic_exercises(session, topic_id)
    by_number = {ex.exercise_number: ex for ex, _ in pairs}
    chunk_by_number: dict[str, int] = {}
    for ex, _ in pairs:
        c = session.scalars(
            select(SourceChunk).where(
                SourceChunk.source_document_id == ex.source_document_id,
                SourceChunk.heading == f"Zadanie {ex.exercise_number}.",
            )
        ).one_or_none()
        if c is not None:
            chunk_by_number[ex.exercise_number] = c.id

    result = agent.extract(KnowledgeRequest(
        topic_code=topic.official_requirement_code or str(topic_id),
        topic_name=topic.name,
        requirement_text=topic.statement_latex or topic.description,
        exercises=[ctx for _, ctx in pairs],
    ))

    _clear_topic(session, topic_id)
    res = ExtractResult(topic.official_requirement_code or str(topic_id), len(pairs))

    def cids(nums: list[str]) -> list[int]:
        return [chunk_by_number[n] for n in nums if n in chunk_by_number]

    def refs(raw: list[str], prose: str | None = None) -> list[str]:
        """Exercise numbers an item is actually backed by. Tolerates the model
        putting "Zadanie 11.1" (not "11.1") in `from_exercises`, and falls back
        to the item's own prose when `from_exercises` is empty — so an item that
        names its task anywhere is still traceable (was: everything intersected
        to nothing and stored as "from Zadanie none")."""
        out: list[str] = []
        for entry in raw:
            for tok in _NUM.findall(entry):
                if tok in by_number and tok not in out:
                    out.append(tok)
        if not out and prose:
            for tok in _PROSE_REF.findall(prose):
                if tok in by_number and tok not in out:
                    out.append(tok)
        return out

    for c in result.concepts:
        cited = refs(c.from_exercises, c.evidence)
        session.add(Concept(
            topic_id=topic_id, name=c.name[:255], description=c.description,
            explanation=c.evidence, difficulty=c.difficulty,
            source_chunk_ids=cids(cited),
        ))
        res.concepts += 1
    for f in result.formulas:
        cited = refs(f.from_exercises, f.evidence)
        session.add(Formula(
            topic_id=topic_id, name=f.name[:255], latex_raw=f.latex_raw,
            description=f.evidence, conditions=f.conditions,
            source_chunk_ids=cids(cited),
        ))
        res.formulas += 1
    for m in result.methods:
        cited = refs(m.from_exercises, m.evidence)
        session.add(Method(
            topic_id=topic_id, name=m.name[:255], when_to_use=m.when_to_use,
            steps=m.steps, source_chunk_ids=cids(cited),
        ))
        res.methods += 1
    for e in result.examples:
        cited = refs(e.from_exercises, e.evidence)
        session.add(Example(
            topic_id=topic_id, statement=e.statement, worked_solution=e.worked_solution,
            difficulty=e.difficulty, source_chunk_ids=cids(cited),
        ))
        res.examples += 1
    for o in result.objectives:
        cited = refs(o.from_exercises, o.evidence)
        session.add(LearningObjective(
            topic_id=topic_id, statement=o.statement, bloom_level=o.bloom_level,
            source_chunk_ids=cids(cited),
        ))
        res.objectives += 1

    for mc in result.misconceptions:
        cited = refs(mc.from_exercises, mc.evidence)
        kind = mc.source_kind
        # An inference (or a claimed distractor) with no exercise behind it is
        # relabelled UNSOURCED — accurate labelling, not suppression (ADR 0011).
        # MARKING_SCHEME / INFORMATOR / DISTRACTOR_INFERENCE that DO cite an
        # exercise are real sources, kept as-is.
        if kind in (MisconceptionSource.AGENT_INFERENCE,
                    MisconceptionSource.DISTRACTOR_INFERENCE) and not cited:
            kind = MisconceptionSource.UNSOURCED
        if kind is MisconceptionSource.UNSOURCED:
            res.unsourced_misconceptions += 1
        # AGENT_INFERENCE and UNSOURCED both go to the reviewer — the item is
        # kept, labelled, and flagged; the human approves or rejects it. Real-
        # source misconceptions still ride the topic's KNOWLEDGE_SPEC card but
        # need no per-item flag.
        if kind in (MisconceptionSource.AGENT_INFERENCE, MisconceptionSource.UNSOURCED):
            res.flagged_misconceptions += 1
            session.add(KnowledgeFlag(
                topic_id=topic_id, kind=FlagKind.GAP, item_kind="misconception",
                detail=f"[{kind.value}] '{mc.name}': {mc.evidence}",
            ))
        session.add(Misconception(
            topic_id=topic_id, name=mc.name[:255], description=mc.evidence,
            incorrect_reasoning=mc.incorrect_reasoning,
            correct_reasoning=mc.correct_reasoning, severity=mc.severity,
            source_kind=kind, distractor=(mc.distractor or None),
            source_chunk_ids=cids(cited),
        ))
        res.misconceptions += 1
        res.misconception_sources[kind.value] = res.misconception_sources.get(kind.value, 0) + 1
        res.misconception_detail.append({
            "name": mc.name, "source_kind": kind.value,
            "from_exercises": cited, "distractor": mc.distractor or None,
            "evidence": mc.evidence[:160],
        })

    for fl in result.flags:
        try:
            fk = FlagKind(fl.kind.upper())
        except ValueError:
            fk = FlagKind.GAP
        session.add(KnowledgeFlag(
            topic_id=topic_id, kind=fk, item_kind=fl.item_kind[:32],
            detail=fl.detail, source_chunk_ids=cids(refs(fl.from_exercises, fl.detail)),
        ))
        res.flags += 1

    session.flush()

    ri = _upsert_review_item(
        session, topic, has_flags=(res.flags + res.flagged_misconceptions) > 0
    )
    res.review_item_id = ri.id
    _upsert_extraction(session, topic_id, agent, len(pairs), ri.id)
    return res


@register(JobType.EXTRACT_KNOWLEDGE)
def handle_extract_knowledge(session: Session, job: Job) -> dict:
    import time

    agent = get_agent()
    t0 = time.monotonic()
    res = extract_topic(
        session, job.input["topic_id"], agent, force=bool(job.input.get("force")),
    )
    elapsed = round(time.monotonic() - t0, 1)
    out = {
        "elapsed_s": elapsed,
        "topic_code": res.topic_code, "exercises": res.exercises,
        "concepts": res.concepts, "formulas": res.formulas, "methods": res.methods,
        "examples": res.examples, "objectives": res.objectives,
        "misconceptions": res.misconceptions,
        "misconception_sources": res.misconception_sources,
        "misconception_detail": res.misconception_detail,
        "flags": res.flags, "unsourced_misconceptions": res.unsourced_misconceptions,
        "flagged_misconceptions": res.flagged_misconceptions,
        "review_item_id": res.review_item_id,
    }
    if getattr(agent, "last_usage", None):
        out["usage"] = agent.last_usage
    return out
