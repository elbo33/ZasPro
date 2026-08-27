"""`MAP_CHUNK` job handler and the `map_document` driver.

This is the "business-rule validation -> database" half of the agent contract
(SPEC §12). The agent returns a `MappingResult`; here it is checked against the
live curriculum (the chosen topic must be a real podstawowy requirement — ADR
0008) and only then written as a `ChunkMapping`.

Queue policy (SPEC §9, §10): a mapping at or above `AUTO_APPROVE_THRESHOLD` is
`AI_SUGGESTED` and stays out of the review queue; below it the mapping is
`REVIEW_REQUIRED` and gets exactly one `ReviewItem`. Deterministic extraction
(chunk confidence NULL) is not itself a reason to review — only an uncertain
*mapping* is.
"""

from __future__ import annotations

import random
import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from zaspro.db.models import (
    ChunkMapping,
    ContentType,
    Exercise,
    Job,
    JobType,
    MappingStatus,
    ReviewItem,
    ReviewItemType,
    ReviewStatus,
    SourceChunk,
    Topic,
    TopicLevel,
)
from zaspro.jobs import enqueue, register
from zaspro.mapping.agent import (
    AUTO_APPROVE_THRESHOLD,
    DEFAULT_AUDIT_SAMPLE_RATE,
    MappingAgent,
    MappingError,
    MappingRequest,
    TopicRef,
    default_agent,
)

_ZADANIE = re.compile(r"Zadanie\s+([\d.]+?)\.?\s*$")

# Injectable so tests and offline scripts run the stub without touching the
# worker's call site (the handler only gets (session, job)).
_AGENT: MappingAgent | None = None


def set_agent(agent: MappingAgent | None) -> None:
    global _AGENT
    _AGENT = agent


def get_agent() -> MappingAgent:
    return _AGENT if _AGENT is not None else default_agent()


def candidate_topics(session: Session) -> list[TopicRef]:
    """Every podstawowy leaf requirement. Rozszerzony is deferred (ADR 0008), so
    it is never offered as a mapping target."""

    rows = session.scalars(
        select(Topic)
        .where(
            Topic.level == TopicLevel.PODSTAWOWY,
            Topic.official_requirement_code.is_not(None),
        )
        .order_by(Topic.official_requirement_code)
    ).all()
    return [
        TopicRef(
            topic_id=t.id,
            code=t.official_requirement_code or "",
            unit=t.unit.code,
            name=t.name,
            level=t.level.value,
        )
        for t in rows
    ]


def _exercise_number_from(chunk: SourceChunk) -> str | None:
    if chunk.heading:
        m = _ZADANIE.search(chunk.heading.strip())
        if m:
            return m.group(1)
    return chunk.section


def _propagate_topic(session: Session, chunk: SourceChunk, topic_id: int | None) -> None:
    """Mirror an accepted mapping onto the matching exercise row so downstream
    milestones (and the coverage histogram) see it. Reversible: passing
    `topic_id=None` clears it."""

    number = _exercise_number_from(chunk)
    if number is None:
        return
    ex = session.scalars(
        select(Exercise).where(
            Exercise.source_document_id == chunk.source_document_id,
            Exercise.exercise_number == number,
        )
    ).one_or_none()
    if ex is not None:
        ex.topic_id = topic_id


def apply_mapping_to_exercise(
    session: Session, mapping: ChunkMapping, *, topic_id: int | None
) -> None:
    """Set (or clear) the exercise's `topic_id` from a mapping decision. Used by
    the auto-suggest path here and by the review queue on approve/reject."""

    chunk = session.get(SourceChunk, mapping.source_chunk_id)
    if chunk is not None:
        _propagate_topic(session, chunk, topic_id)


def _drop_review_item(session: Session, mapping_id: int) -> None:
    item = session.scalars(
        select(ReviewItem).where(
            ReviewItem.item_type == ReviewItemType.CURRICULUM_MAPPING,
            ReviewItem.ref_table == "chunk_mappings",
            ReviewItem.ref_id == mapping_id,
        )
    ).one_or_none()
    if item is not None:
        session.delete(item)
        session.flush()


def _audit_pick(chunk_id: int, prompt_version: str | None, rate: float) -> bool:
    """Deterministic per (chunk, prompt version) so a re-run is stable and a new
    prompt re-rolls the sample."""

    if rate <= 0:
        return False
    if rate >= 1:
        return True
    return random.Random(f"{chunk_id}:{prompt_version}").random() < rate


def map_chunk(
    session: Session,
    source_chunk_id: int,
    agent: MappingAgent | None = None,
    *,
    threshold: float = AUTO_APPROVE_THRESHOLD,
    audit_sample_rate: float = DEFAULT_AUDIT_SAMPLE_RATE,
    remap: bool = False,
) -> ChunkMapping:
    agent = agent or get_agent()
    chunk = session.get(SourceChunk, source_chunk_id)
    if chunk is None:
        raise MappingError(f"source_chunk {source_chunk_id} not found")

    existing = session.scalars(
        select(ChunkMapping).where(ChunkMapping.source_chunk_id == source_chunk_id)
    ).one_or_none()
    if existing is not None and not remap:
        return existing

    candidates = candidate_topics(session)
    valid_ids = {c.topic_id for c in candidates}

    result = agent.map(
        MappingRequest(
            source_chunk_id=source_chunk_id,
            heading=chunk.heading,
            text=chunk.text,
            latex=chunk.latex,
            current_content_type=chunk.content_type,
            candidates=candidates,
        )
    )

    # business-rule validation (SPEC §12) — prompts are suggestions, this is the
    # guarantee
    if result.topic_id is not None and result.topic_id not in valid_ids:
        raise MappingError(
            f"agent chose topic_id={result.topic_id}, which is not a podstawowy "
            f"requirement ({len(valid_ids)} valid candidates)"
        )
    if not isinstance(result.content_type, ContentType):
        raise MappingError(f"content_type {result.content_type!r} is not valid")

    status = (
        MappingStatus.AI_SUGGESTED
        if result.confidence >= threshold
        else MappingStatus.REVIEW_REQUIRED
    )

    if existing is not None:
        _drop_review_item(session, existing.id)
        mapping = existing
    else:
        mapping = ChunkMapping(source_chunk_id=source_chunk_id)
        session.add(mapping)

    mapping.topic_id = result.topic_id
    mapping.content_type = result.content_type
    mapping.difficulty = result.difficulty
    mapping.confidence = result.confidence
    mapping.mapping_status = status
    mapping.rationale = result.rationale
    mapping.model = agent.model
    mapping.prompt_version = agent.prompt_version
    session.flush()

    code = next((c.code for c in candidates if c.topic_id == result.topic_id), None)

    if status is MappingStatus.AI_SUGGESTED:
        # a confident mapping is applied straight away; the audit sampler may
        # still queue a copy for a human spot-check without blocking it
        _propagate_topic(session, chunk, result.topic_id)
        if _audit_pick(chunk.id, agent.prompt_version, audit_sample_rate):
            session.add(
                ReviewItem(
                    item_type=ReviewItemType.CURRICULUM_MAPPING,
                    ref_table="chunk_mappings",
                    ref_id=mapping.id,
                    status=ReviewStatus.OPEN,
                    risk=min(0.2, round(1.0 - result.confidence, 4)),
                    confidence=result.confidence,
                    title=f"[audit] {chunk.heading or 'chunk ' + str(chunk.id)} → {code or 'unmapped'}",
                    topic_id=result.topic_id,
                    source_document_id=chunk.source_document_id,
                    audit_sample=True,
                )
            )
            session.flush()
    else:
        _propagate_topic(session, chunk, None)  # don't carry an unreviewed guess
        session.add(
            ReviewItem(
                item_type=ReviewItemType.CURRICULUM_MAPPING,
                ref_table="chunk_mappings",
                ref_id=mapping.id,
                status=ReviewStatus.OPEN,
                risk=round(1.0 - result.confidence, 4),
                confidence=result.confidence,
                title=f"{chunk.heading or 'chunk ' + str(chunk.id)} → {code or 'unmapped'}",
                topic_id=result.topic_id,
                source_document_id=chunk.source_document_id,
            )
        )
        session.flush()

    return mapping


@register(JobType.MAP_CHUNK)
def handle_map_chunk(session: Session, job: Job) -> dict:
    threshold = job.input.get("threshold", AUTO_APPROVE_THRESHOLD)
    audit_rate = job.input.get("audit_sample_rate", DEFAULT_AUDIT_SAMPLE_RATE)
    mapping = map_chunk(
        session,
        job.input["source_chunk_id"],
        get_agent(),
        threshold=threshold,
        audit_sample_rate=audit_rate,
    )
    return {
        "chunk_mapping_id": mapping.id,
        "topic_id": mapping.topic_id,
        "confidence": mapping.confidence,
        "mapping_status": mapping.mapping_status.value,
    }


def map_document(
    session: Session,
    source_document_id: int,
    agent: MappingAgent | None = None,
    *,
    inline: bool = False,
    threshold: float = AUTO_APPROVE_THRESHOLD,
    audit_sample_rate: float = DEFAULT_AUDIT_SAMPLE_RATE,
) -> dict:
    """Map every not-yet-mapped chunk of a document. `inline=True` runs the
    agent now (offline scripts, tests); the default enqueues `MAP_CHUNK` jobs.

    `threshold` is the auto-approve cutoff on mapping confidence. Pass a value
    above 1.0 to force every mapping into the review queue — the calibration
    run where a human grades the agent's confidence against their own verdict
    before the cutoff is fixed from evidence. `audit_sample_rate` is the
    permanent fraction of confident mappings queued for a spot-check regardless
    of the threshold."""

    agent = agent or get_agent()
    chunk_ids = session.scalars(
        select(SourceChunk.id)
        .outerjoin(ChunkMapping, ChunkMapping.source_chunk_id == SourceChunk.id)
        .where(
            SourceChunk.source_document_id == source_document_id,
            ChunkMapping.id.is_(None),
        )
        .order_by(SourceChunk.order_index)
    ).all()

    summary = {"chunks": len(chunk_ids), "auto": 0, "review": 0, "unmapped": 0, "jobs": 0}
    if not inline:
        for cid in chunk_ids:
            enqueue(
                session, JobType.MAP_CHUNK,
                {
                    "source_chunk_id": cid,
                    "threshold": threshold,
                    "audit_sample_rate": audit_sample_rate,
                },
            )
            summary["jobs"] += 1
        return summary

    for cid in chunk_ids:
        m = map_chunk(
            session, cid, agent,
            threshold=threshold, audit_sample_rate=audit_sample_rate,
        )
        if m.mapping_status is MappingStatus.AI_SUGGESTED:
            summary["auto"] += 1
        else:
            summary["review"] += 1
        if m.topic_id is None:
            summary["unmapped"] += 1
    return summary
