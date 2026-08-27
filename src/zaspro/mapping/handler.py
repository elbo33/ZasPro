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

from sqlalchemy import func, select
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


def _drop_review_items_for(session: Session, mapping_ids: list[int]) -> None:
    if not mapping_ids:
        return
    items = session.scalars(
        select(ReviewItem).where(
            ReviewItem.item_type == ReviewItemType.CURRICULUM_MAPPING,
            ReviewItem.ref_table == "chunk_mappings",
            ReviewItem.ref_id.in_(mapping_ids),
        )
    ).all()
    for item in items:
        session.delete(item)
    if items:
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
    ).all()
    if existing and not remap:
        return next(m for m in existing if m.is_primary)

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
            f"agent chose primary topic_id={result.topic_id}, which is not a "
            f"podstawowy requirement ({len(valid_ids)} valid candidates)"
        )
    if not isinstance(result.content_type, ContentType):
        raise MappingError(f"content_type {result.content_type!r} is not valid")

    # secondaries: in the candidate set, distinct, and not the primary
    secondaries: list = []
    seen: set[int] = {result.topic_id} if result.topic_id is not None else set()
    for sec in result.secondary_topics:
        if sec.topic_id not in valid_ids:
            raise MappingError(
                f"agent gave secondary topic_id={sec.topic_id}, not a podstawowy "
                "requirement"
            )
        if sec.topic_id in seen:
            continue  # duplicate, or same as primary — silently drop
        seen.add(sec.topic_id)
        secondaries.append(sec)

    status = (
        MappingStatus.AI_SUGGESTED
        if result.confidence >= threshold
        else MappingStatus.REVIEW_REQUIRED
    )

    # replace every prior row for this chunk (and its review item) wholesale
    _drop_review_items_for(session, [m.id for m in existing])
    for m in existing:
        session.delete(m)
    if existing:
        session.flush()

    primary = ChunkMapping(
        source_chunk_id=source_chunk_id,
        is_primary=True,
        topic_id=result.topic_id,
        content_type=result.content_type,
        difficulty=result.difficulty,
        confidence=result.confidence,
        mapping_status=status,
        rationale=result.rationale,
        model=agent.model,
        prompt_version=agent.prompt_version,
    )
    session.add(primary)
    session.flush()

    for sec in secondaries:
        session.add(
            ChunkMapping(
                source_chunk_id=source_chunk_id,
                is_primary=False,
                topic_id=sec.topic_id,
                content_type=result.content_type,
                difficulty=result.difficulty,
                confidence=sec.confidence,
                mapping_status=MappingStatus.AI_SUGGESTED,
                rationale=sec.rationale,
                model=agent.model,
                prompt_version=agent.prompt_version,
            )
        )
    session.flush()

    code = next((c.code for c in candidates if c.topic_id == result.topic_id), None)
    _place_review_item(
        session, chunk, primary, code, status,
        audit=(
            status is MappingStatus.AI_SUGGESTED
            and _audit_pick(chunk.id, agent.prompt_version, audit_sample_rate)
        ),
    )
    # transient: token usage from this call, for cost reporting (not persisted
    # on the row). None for the stub.
    primary._call_usage = getattr(agent, "last_usage", None)  # type: ignore[attr-defined]
    return primary


def _place_review_item(
    session: Session,
    chunk: SourceChunk,
    primary: ChunkMapping,
    code: str | None,
    status: MappingStatus,
    *,
    audit: bool,
) -> None:
    if status is MappingStatus.AI_SUGGESTED:
        # a confident primary is applied straight away; the audit sampler may
        # still queue a copy for a spot-check without blocking it
        _propagate_topic(session, chunk, primary.topic_id)
        if not audit:
            return
        risk = min(0.2, round(1.0 - primary.confidence, 4))
        title = f"[audit] {chunk.heading or 'chunk ' + str(chunk.id)} → {code or 'unmapped'}"
    else:
        _propagate_topic(session, chunk, None)  # don't carry an unreviewed guess
        risk = round(1.0 - primary.confidence, 4)
        title = f"{chunk.heading or 'chunk ' + str(chunk.id)} → {code or 'unmapped'}"

    session.add(
        ReviewItem(
            item_type=ReviewItemType.CURRICULUM_MAPPING,
            ref_table="chunk_mappings",
            ref_id=primary.id,
            status=ReviewStatus.OPEN,
            risk=risk,
            confidence=primary.confidence,
            title=title,
            topic_id=primary.topic_id,
            source_document_id=chunk.source_document_id,
            audit_sample=audit,
        )
    )
    session.flush()


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
        remap=job.input.get("remap", False),
    )
    out: dict = {
        "chunk_mapping_id": mapping.id,
        "topic_id": mapping.topic_id,
        "confidence": mapping.confidence,
        "mapping_status": mapping.mapping_status.value,
    }
    usage = getattr(mapping, "_call_usage", None)
    if usage is not None:
        out["usage"] = {"in": usage.input_tokens, "out": usage.output_tokens}
    return out


def map_document(
    session: Session,
    source_document_id: int,
    agent: MappingAgent | None = None,
    *,
    inline: bool = False,
    threshold: float = AUTO_APPROVE_THRESHOLD,
    audit_sample_rate: float = DEFAULT_AUDIT_SAMPLE_RATE,
    remap: bool = False,
) -> dict:
    """Map the document's chunks. `inline=True` runs the agent now (offline
    scripts, tests); the default enqueues `MAP_CHUNK` jobs.

    Without `remap`, only chunks that have no mapping yet are touched. With
    `remap=True` every chunk is re-run: its prior `ChunkMapping` and any review
    item are dropped and rebuilt (used to re-map a document with a different
    agent — e.g. stub -> Claude for the calibration pass).

    `threshold` is the auto-approve cutoff on mapping confidence; pass a value
    above 1.0 to force every mapping into the review queue. `audit_sample_rate`
    is the permanent fraction of confident mappings queued for a spot-check
    regardless of the threshold."""

    agent = agent or get_agent()
    stmt = select(SourceChunk.id).where(
        SourceChunk.source_document_id == source_document_id
    )
    if not remap:
        stmt = stmt.outerjoin(
            ChunkMapping,
            (ChunkMapping.source_chunk_id == SourceChunk.id)
            & ChunkMapping.is_primary.is_(True),
        ).where(ChunkMapping.id.is_(None))
    chunk_ids = session.scalars(stmt.order_by(SourceChunk.order_index)).all()

    total_chunks = session.scalar(
        select(func.count())
        .select_from(SourceChunk)
        .where(SourceChunk.source_document_id == source_document_id)
    ) or 0

    summary = {
        "chunks": total_chunks,
        "selected": len(chunk_ids),
        "auto": 0,
        "review": 0,
        "unmapped": 0,
        "jobs": 0,
        "remap": remap,
    }
    if not inline:
        for cid in chunk_ids:
            enqueue(
                session, JobType.MAP_CHUNK,
                {
                    "source_chunk_id": cid,
                    "threshold": threshold,
                    "audit_sample_rate": audit_sample_rate,
                    "remap": remap,
                },
            )
            summary["jobs"] += 1
        return summary

    for cid in chunk_ids:
        m = map_chunk(
            session, cid, agent,
            threshold=threshold, audit_sample_rate=audit_sample_rate, remap=remap,
        )
        if m.mapping_status is MappingStatus.AI_SUGGESTED:
            summary["auto"] += 1
        else:
            summary["review"] += 1
        if m.topic_id is None:
            summary["unmapped"] += 1
    return summary
