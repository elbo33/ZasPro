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
    Topic,
    Unit,
)

router = APIRouter(prefix="/curriculum", tags=["curriculum"])


@router.get("", response_model=list[CurriculumUnit])
def get_curriculum(
    level: str = "podstawowy", db: Session = Depends(get_db)
) -> list[CurriculumUnit]:
    # per topic: chunks where this is the PRIMARY requirement (primarily drills
    # it) vs chunks where it is only a secondary (also touches it). Different
    # things — see m3/mapping_multitopic_scan.md.
    primary: dict[int, int] = {}
    approved: dict[int, int] = {}
    secondary: dict[int, int] = {}
    for topic_id, is_primary, status, n in db.execute(
        select(
            ChunkMapping.topic_id,
            ChunkMapping.is_primary,
            ChunkMapping.mapping_status,
            func.count(),
        )
        .where(ChunkMapping.topic_id.is_not(None))
        .group_by(
            ChunkMapping.topic_id, ChunkMapping.is_primary, ChunkMapping.mapping_status
        )
    ):
        if is_primary:
            primary[topic_id] = primary.get(topic_id, 0) + n
            if status is MappingStatus.APPROVED:
                approved[topic_id] = approved.get(topic_id, 0) + n
        else:
            secondary[topic_id] = secondary.get(topic_id, 0) + n

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
                        mapped_chunks=primary.get(t.id, 0),
                        also_tests=secondary.get(t.id, 0),
                        approved_chunks=approved.get(t.id, 0),
                        exercises=ex_counts.get(t.id, 0),
                    )
                    for t in sorted(topics, key=lambda x: x.order_index)
                ],
            )
        )
    return out
