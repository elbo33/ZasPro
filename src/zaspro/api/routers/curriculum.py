"""Curriculum tree endpoint (SPEC §17 dashboard skeleton). Read-only.

Each topic carries its mapped / approved chunk counts and exercise count so the
tree doubles as a coverage view (SPEC §10: unmapped volume is a signal)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from zaspro.api.deps import get_db
from zaspro.api.schemas import CurriculumTopic, CurriculumUnit
from zaspro.db.models import (
    ChunkMapping,
    Exercise,
    MappingStatus,
    SourceChunk,
    Topic,
    Unit,
)

router = APIRouter(prefix="/curriculum", tags=["curriculum"])


@router.get("", response_model=list[CurriculumUnit])
def get_curriculum(
    level: str = "podstawowy", db: Session = Depends(get_db)
) -> list[CurriculumUnit]:
    # mapped / approved chunk counts per topic
    mapped: dict[int, int] = {}
    approved: dict[int, int] = {}
    for topic_id, status, n in db.execute(
        select(ChunkMapping.topic_id, ChunkMapping.mapping_status, func.count())
        .join(SourceChunk, SourceChunk.id == ChunkMapping.source_chunk_id)
        .where(ChunkMapping.topic_id.is_not(None))
        .group_by(ChunkMapping.topic_id, ChunkMapping.mapping_status)
    ):
        mapped[topic_id] = mapped.get(topic_id, 0) + n
        if status is MappingStatus.APPROVED:
            approved[topic_id] = approved.get(topic_id, 0) + n

    ex_counts: dict[int, int] = {}
    for topic_id, n in db.execute(
        select(Exercise.topic_id, func.count())
        .where(Exercise.topic_id.is_not(None))
        .group_by(Exercise.topic_id)
    ):
        ex_counts[topic_id] = n

    out: list[CurriculumUnit] = []
    units = db.scalars(select(Unit).order_by(Unit.order_index)).all()
    for u in units:
        topics = [t for t in u.topics if t.level.value == level]
        if not topics:
            continue
        out.append(
            CurriculumUnit(
                id=u.id,
                code=u.code,
                name=u.name,
                topics=[
                    CurriculumTopic(
                        id=t.id,
                        code=t.official_requirement_code,
                        name=t.name,
                        level=t.level.value,
                        parent_id=t.parent_id,
                        mapped_chunks=mapped.get(t.id, 0),
                        approved_chunks=approved.get(t.id, 0),
                        exercises=ex_counts.get(t.id, 0),
                    )
                    for t in sorted(topics, key=lambda x: x.order_index)
                ],
            )
        )
    return out
