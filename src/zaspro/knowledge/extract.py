"""Per-topic knowledge extraction: build the request, call the agent,
business-rule-validate (SPEC §11/§12), persist. `EXTRACT_KNOWLEDGE` job.

Aggregation is over `exercise_topics` — PRIMARY ∪ approved SECONDARY (ADR 0010),
via `Exercise.full_statement` (stem + body), never `SourceChunk.text` alone.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from zaspro.db.models import (
    Concept, Example, Exercise, ExerciseTopic, Formula, Job, JobType,
    KnowledgeFlag, FlagKind, LearningObjective, Method, Misconception,
    MisconceptionSource, SourceChunk, SourceDocument, Topic,
)
from zaspro.jobs import register
from zaspro.knowledge.agent import (
    ExerciseCtx, KnowledgeAgent, KnowledgeError, KnowledgeRequest, get_agent,
)

_ZAD = re.compile(r"^Zadanie\s+(\d+(?:\.\d+)?)\.?\s*\(0", re.MULTILINE)
_BLOCK_START = re.compile(r"Zasady oceniania")
_BLOCK_END = re.compile(r"Rozwiązanie|Przykład|Komentarz|Schemat|Uwaga")


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


def extract_topic(
    session: Session, topic_id: int, agent: KnowledgeAgent | None = None
) -> ExtractResult:
    agent = agent or get_agent()
    topic = session.get(Topic, topic_id)
    if topic is None:
        raise KnowledgeError(f"topic {topic_id} not found")

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

    def valid(nums: list[str]) -> list[str]:
        return [n for n in nums if n in by_number]

    for c in result.concepts:
        session.add(Concept(
            topic_id=topic_id, name=c.name[:255], description=c.description,
            explanation=c.evidence, difficulty=c.difficulty,
            source_chunk_ids=cids(valid(c.from_exercises)),
        ))
        res.concepts += 1
    for f in result.formulas:
        session.add(Formula(
            topic_id=topic_id, name=f.name[:255], latex_raw=f.latex_raw,
            description=f.evidence, conditions=f.conditions,
            source_chunk_ids=cids(valid(f.from_exercises)),
        ))
        res.formulas += 1
    for m in result.methods:
        session.add(Method(
            topic_id=topic_id, name=m.name[:255], when_to_use=m.when_to_use,
            steps=m.steps, source_chunk_ids=cids(valid(m.from_exercises)),
        ))
        res.methods += 1
    for e in result.examples:
        session.add(Example(
            topic_id=topic_id, statement=e.statement, worked_solution=e.worked_solution,
            difficulty=e.difficulty, source_chunk_ids=cids(valid(e.from_exercises)),
        ))
        res.examples += 1
    for o in result.objectives:
        session.add(LearningObjective(
            topic_id=topic_id, statement=o.statement, bloom_level=o.bloom_level,
            source_chunk_ids=cids(valid(o.from_exercises)),
        ))
        res.objectives += 1

    for mc in result.misconceptions:
        cited = valid(mc.from_exercises)
        kind = mc.source_kind
        # SPEC §11: an inference with no exercise behind it is unsourced
        if kind is MisconceptionSource.AGENT_INFERENCE and not cited:
            kind = MisconceptionSource.UNSOURCED
        if kind is MisconceptionSource.UNSOURCED:
            res.unsourced_misconceptions += 1
            session.add(KnowledgeFlag(
                topic_id=topic_id, kind=FlagKind.GAP, item_kind="misconception",
                detail=f"unsourced misconception '{mc.name}': {mc.evidence}",
            ))
        session.add(Misconception(
            topic_id=topic_id, name=mc.name[:255], description=mc.evidence,
            incorrect_reasoning=mc.incorrect_reasoning,
            correct_reasoning=mc.correct_reasoning, severity=mc.severity,
            source_kind=kind, source_chunk_ids=cids(cited),
        ))
        res.misconceptions += 1
        res.misconception_sources[kind.value] = res.misconception_sources.get(kind.value, 0) + 1
        res.misconception_detail.append({
            "name": mc.name, "source_kind": kind.value,
            "from_exercises": cited, "evidence": mc.evidence[:160],
        })

    for fl in result.flags:
        try:
            fk = FlagKind(fl.kind.upper())
        except ValueError:
            fk = FlagKind.GAP
        session.add(KnowledgeFlag(
            topic_id=topic_id, kind=fk, item_kind=fl.item_kind[:32],
            detail=fl.detail, source_chunk_ids=cids(valid(fl.from_exercises)),
        ))
        res.flags += 1

    session.flush()
    return res


@register(JobType.EXTRACT_KNOWLEDGE)
def handle_extract_knowledge(session: Session, job: Job) -> dict:
    agent = get_agent()
    res = extract_topic(session, job.input["topic_id"], agent)
    out = {
        "topic_code": res.topic_code, "exercises": res.exercises,
        "concepts": res.concepts, "formulas": res.formulas, "methods": res.methods,
        "examples": res.examples, "objectives": res.objectives,
        "misconceptions": res.misconceptions,
        "misconception_sources": res.misconception_sources,
        "misconception_detail": res.misconception_detail,
        "flags": res.flags, "unsourced_misconceptions": res.unsourced_misconceptions,
    }
    if getattr(agent, "last_usage", None):
        out["usage"] = agent.last_usage
    return out
