"""Materialise `exercise_topics` from the reviewed `chunk_mappings` (SPEC §11).

Built **before** the knowledge agent runs. A topic's exercises for aggregation
are those where it is the PRIMARY or an approved SECONDARY mapping — extracting
from primaries only rebuilds the narrow view multi-topic mapping removed
(SPEC §10, §17, ADR for M4).

"Approved" here means the chunk's **primary** mapping is `AI_SUGGESTED`
(auto-approved, at or above `AUTO_APPROVE_THRESHOLD`) or human `APPROVED` — not
`REJECTED`, not still `REVIEW_REQUIRED`. Secondary rows ride on that decision.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from zaspro.db.models import (
    ChunkMapping,
    Exercise,
    ExerciseTopic,
    MappingStatus,
    SourceChunk,
    Topic,
    TopicLevel,
    TopicRole,
)

_ACCEPTED = (MappingStatus.AI_SUGGESTED, MappingStatus.APPROVED)


@dataclass
class RebuildResult:
    exercises_seen: int
    exercises_with_topics: int
    skipped_unsettled: int  # primary mapping rejected or still pending
    skipped_no_mapping: int
    primary_rows: int
    secondary_rows: int


def _chunk_for(session: Session, ex: Exercise) -> SourceChunk | None:
    if ex.source_document_id is None:
        return None
    return session.scalars(
        select(SourceChunk).where(
            SourceChunk.source_document_id == ex.source_document_id,
            SourceChunk.heading == f"Zadanie {ex.exercise_number}.",
        )
    ).one_or_none()


def rebuild_exercise_topics(session: Session) -> RebuildResult:
    session.query(ExerciseTopic).delete()
    session.flush()

    res = RebuildResult(0, 0, 0, 0, 0, 0)
    exercises = session.scalars(select(Exercise)).all()
    for ex in exercises:
        res.exercises_seen += 1
        chunk = _chunk_for(session, ex)
        if chunk is None:
            res.skipped_no_mapping += 1
            continue
        mappings = session.scalars(
            select(ChunkMapping).where(ChunkMapping.source_chunk_id == chunk.id)
        ).all()
        primary = next((m for m in mappings if m.is_primary), None)
        if primary is None:
            res.skipped_no_mapping += 1
            continue
        if primary.mapping_status not in _ACCEPTED:
            res.skipped_unsettled += 1
            continue

        added_topics: set[int] = set()
        if primary.topic_id is not None:
            session.add(ExerciseTopic(
                exercise_id=ex.id, topic_id=primary.topic_id,
                role=TopicRole.PRIMARY, confidence=primary.confidence,
                source_chunk_mapping_id=primary.id,
            ))
            added_topics.add(primary.topic_id)
            res.primary_rows += 1

        for sec in mappings:
            if sec.is_primary or sec.topic_id is None or sec.topic_id in added_topics:
                continue
            session.add(ExerciseTopic(
                exercise_id=ex.id, topic_id=sec.topic_id,
                role=TopicRole.SECONDARY, confidence=sec.confidence,
                source_chunk_mapping_id=sec.id,
            ))
            added_topics.add(sec.topic_id)
            res.secondary_rows += 1

        if added_topics:
            res.exercises_with_topics += 1
    session.flush()
    return res


@dataclass
class TopicCount:
    code: str | None
    name: str
    primary: int   # exercises whose primary requirement is this topic
    touch: int     # distinct exercises where this topic is primary OR secondary


def topic_chunk_counts(session: Session) -> list[TopicCount]:
    """Per podstawowy requirement, the exercise count under each definition."""

    prim: dict[int, int] = dict(
        session.execute(
            select(ExerciseTopic.topic_id, func.count())
            .where(ExerciseTopic.role == TopicRole.PRIMARY)
            .group_by(ExerciseTopic.topic_id)
        ).all()
    )
    touch: dict[int, int] = dict(
        session.execute(
            select(ExerciseTopic.topic_id, func.count(func.distinct(ExerciseTopic.exercise_id)))
            .group_by(ExerciseTopic.topic_id)
        ).all()
    )
    topics = session.scalars(
        select(Topic)
        .where(Topic.level == TopicLevel.PODSTAWOWY, Topic.official_requirement_code.is_not(None))
        .order_by(Topic.official_requirement_code)
    ).all()
    return [
        TopicCount(t.official_requirement_code, t.name, prim.get(t.id, 0), touch.get(t.id, 0))
        for t in topics
    ]
