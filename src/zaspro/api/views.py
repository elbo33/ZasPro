"""Shared serialisers: ORM row -> response schema. Used by more than one router."""

from __future__ import annotations

from sqlalchemy.orm import Session

from zaspro.api.schemas import MappingView, ReviewItemView, TopicOption
from zaspro.db.models import ChunkMapping, ReviewItem, ReviewItemType, SourceChunk, Topic
from zaspro.mapping.handler import candidate_topics


def mapping_view(session: Session, mapping: ChunkMapping) -> MappingView:
    code = None
    if mapping.topic_id is not None:
        t = session.get(Topic, mapping.topic_id)
        code = t.official_requirement_code if t else None
    return MappingView(
        id=mapping.id,
        source_chunk_id=mapping.source_chunk_id,
        topic_id=mapping.topic_id,
        topic_code=code,
        content_type=mapping.content_type.value,
        difficulty=mapping.difficulty,
        confidence=mapping.confidence,
        mapping_status=mapping.mapping_status.value,
        rationale=mapping.rationale,
        model=mapping.model,
        prompt_version=mapping.prompt_version,
    )


def item_view(session: Session, item: ReviewItem, *, with_candidates: bool) -> ReviewItemView:
    view = ReviewItemView(
        id=item.id,
        item_type=item.item_type.value,
        status=item.status.value,
        risk=item.risk,
        confidence=item.confidence,
        title=item.title,
        topic_id=item.topic_id,
        source_document_id=item.source_document_id,
        created_at=item.created_at,
        audit_sample=item.audit_sample,
    )
    if item.item_type is ReviewItemType.CURRICULUM_MAPPING:
        mapping = session.get(ChunkMapping, item.ref_id)
        if mapping is not None:
            view.mapping = mapping_view(session, mapping)
            chunk = session.get(SourceChunk, mapping.source_chunk_id)
            if chunk is not None:
                view.chunk_heading = chunk.heading
                view.chunk_text = chunk.text
                view.chunk_latex = chunk.latex
        if with_candidates:
            view.candidates = [
                TopicOption(topic_id=c.topic_id, code=c.code, unit=c.unit, name=c.name)
                for c in candidate_topics(session)
            ]
    return view
