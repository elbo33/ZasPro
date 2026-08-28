"""Shared serialisers: ORM row -> response schema. Used by more than one router."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from zaspro.api.schemas import (
    KnowledgeItemView,
    KnowledgeSpecView,
    MappingView,
    ReviewItemView,
    TopicOption,
)
from zaspro.db.models import (
    ChunkMapping,
    Concept,
    Example,
    Formula,
    LearningObjective,
    Method,
    Misconception,
    ReviewItem,
    ReviewItemType,
    Section,
    SectionSpec,
    SourceChunk,
    Topic,
)
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


_KNOWLEDGE_KINDS = [
    ("concept", Concept), ("formula", Formula), ("method", Method),
    ("example", Example), ("objective", LearningObjective),
    ("misconception", Misconception),
]


def knowledge_spec_view(session: Session, section_id: int) -> KnowledgeSpecView | None:
    section = session.get(Section, section_id)
    if section is None:
        return None
    spec = session.scalars(
        select(SectionSpec).where(SectionSpec.section_id == section_id)
    ).one_or_none()
    codes = sorted(
        session.get(Topic, sr.topic_id).official_requirement_code
        for sr in section.requirements
    )

    items: list[KnowledgeItemView] = []
    counts: dict[str, int] = {}
    for kind, model in _KNOWLEDGE_KINDS:
        for obj in session.scalars(
            select(model).where(model.section_id == section_id).order_by(model.order_index, model.id)
        ):
            counts[kind] = counts.get(kind, 0) + 1
            title = getattr(obj, "name", None) or (getattr(obj, "statement", "") or "")[:80]
            detail = (
                getattr(obj, "description", None)
                or getattr(obj, "when_to_use", None)
                or getattr(obj, "worked_solution", None)
                or getattr(obj, "incorrect_reasoning", None)
            )
            items.append(KnowledgeItemView(
                kind=kind, id=obj.id,
                status=obj.verification_status.value,
                title=title, detail=detail,
                extra=getattr(obj, "explanation", None) or getattr(obj, "correct_reasoning", None)
                or getattr(obj, "conditions", None),
            ))

    return KnowledgeSpecView(
        section_id=section_id,
        slug=section.slug,
        name=section.name,
        scope=section.scope,
        requirement_codes=codes,
        written_at=spec.written_at if spec else None,
        prompt_version=spec.prompt_version if spec else None,
        model=spec.model if spec else None,
        exported_at=spec.exported_at if spec else None,
        items=items, counts=counts,
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
    elif item.item_type is ReviewItemType.KNOWLEDGE_SPEC:
        view.knowledge = knowledge_spec_view(session, item.ref_id)
    return view
