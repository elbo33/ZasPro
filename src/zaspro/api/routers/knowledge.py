"""Knowledge-layer endpoints (M4, ADR 0011).

`GET /knowledge` — the index: one row per podstawowy requirement with its
extraction / review / export state, for the dashboard's Knowledge page.
`GET /knowledge/{topic_id}` — the full spec (same shape the review card uses).
`POST /knowledge/{topic_id}/export` — write the committed YAML once the review
card is resolved. Refuses while the card is OPEN.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from zaspro.api.deps import get_db
from zaspro.api.schemas import ExportResult, KnowledgeIndexRow, KnowledgeSpecView
from zaspro.api.views import _KNOWLEDGE_KINDS, knowledge_spec_view
from zaspro.db.models import (
    KnowledgeExtraction,
    KnowledgeProvenance,
    ReviewItem,
    ReviewItemType,
    Topic,
    TopicLevel,
)
from zaspro.knowledge.export import ExportError, export_topic

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.get("", response_model=list[KnowledgeIndexRow])
def get_index(db: Session = Depends(get_db)) -> list[KnowledgeIndexRow]:
    topics = db.scalars(
        select(Topic).where(
            Topic.level == TopicLevel.PODSTAWOWY,
            Topic.official_requirement_code.is_not(None),
        )
    ).all()
    kes = {
        k.topic_id: k
        for k in db.scalars(select(KnowledgeExtraction))
    }
    ris = {
        (r.ref_id): r
        for r in db.scalars(
            select(ReviewItem).where(ReviewItem.item_type == ReviewItemType.KNOWLEDGE_SPEC)
        )
    }
    rows: list[KnowledgeIndexRow] = []
    for t in sorted(topics, key=lambda x: x.official_requirement_code or ""):
        spec = knowledge_spec_view(db, t.id)
        ke = kes.get(t.id)
        ri = ris.get(t.id)
        agent_only = 0
        for _kind, model in _KNOWLEDGE_KINDS:
            agent_only += db.query(model).filter(
                model.topic_id == t.id,
                model.provenance == KnowledgeProvenance.AGENT_KNOWLEDGE,
            ).count()
        rows.append(KnowledgeIndexRow(
            topic_id=t.id,
            code=t.official_requirement_code,
            name=t.name,
            unit=f"{t.unit.code} {t.unit.name}" if t.unit else None,
            exercises=ke.exercises if ke else 0,
            counts=spec.counts if spec else {},
            agent_knowledge_items=agent_only,
            review_status=ri.status.value if ri else None,
            review_item_id=ri.id if ri else None,
            exported_at=ke.exported_at if ke else None,
            prompt_version=ke.prompt_version if ke else None,
        ))
    return rows


@router.get("/{topic_id}", response_model=KnowledgeSpecView)
def get_spec(topic_id: int, db: Session = Depends(get_db)) -> KnowledgeSpecView:
    spec = knowledge_spec_view(db, topic_id)
    if spec is None:
        raise HTTPException(status_code=404, detail=f"topic {topic_id} not found")
    return spec


@router.post("/{topic_id}/export", response_model=ExportResult)
def post_export(
    topic_id: int, reviewer: str = "reviewer", db: Session = Depends(get_db)
) -> ExportResult:
    topic = db.get(Topic, topic_id)
    code = topic.official_requirement_code if topic else str(topic_id)
    try:
        path = export_topic(db, topic_id, reviewer=reviewer)
    except ExportError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    return ExportResult(ok=True, code=code or str(topic_id), path=str(path))
