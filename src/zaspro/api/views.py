"""Shared serialisers: ORM row -> response schema. Used by more than one router."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from zaspro.api.schemas import MappingView, ReviewItemView, TopicOption
from zaspro.db.models import ChunkMapping, ReviewItem, ReviewItemType, SourceChunk, Topic
from zaspro.mapping.handler import candidate_topics, _parent_chunk


def mapping_view(session: Session, mapping: ChunkMapping) -> MappingView:
    code = name = None
    if mapping.topic_id is not None:
        t = session.get(Topic, mapping.topic_id)
        if t is not None:
            code, name = t.official_requirement_code, t.name
    return MappingView(
        id=mapping.id,
        source_chunk_id=mapping.source_chunk_id,
        topic_id=mapping.topic_id,
        topic_code=code,
        topic_name=name,
        is_primary=mapping.is_primary,
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
            # the other requirements this fragment also tests — the reviewer
            # cannot judge whether the primary is the *right* primary without
            # seeing what it was chosen over
            secs = session.scalars(
                select(ChunkMapping)
                .where(
                    ChunkMapping.source_chunk_id == mapping.source_chunk_id,
                    ChunkMapping.is_primary.is_(False),
                )
                .order_by(ChunkMapping.confidence.desc(), ChunkMapping.id)
            ).all()
            view.secondaries = [mapping_view(session, s) for s in secs]
            chunk = session.get(SourceChunk, mapping.source_chunk_id)
            if chunk is not None:
                view.chunk_heading = chunk.heading
                view.chunk_text = chunk.text
                view.chunk_latex = chunk.latex
                parent = _parent_chunk(session, chunk)
                if parent is not None:
                    view.chunk_stem = parent.text
        if with_candidates:
            view.candidates = [
                TopicOption(topic_id=c.topic_id, code=c.code, unit=c.unit, name=c.name)
                for c in candidate_topics(session)
            ]
    return view
