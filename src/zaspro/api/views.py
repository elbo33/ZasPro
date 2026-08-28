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
    KnowledgeExtraction,
    KnowledgeFlag,
    LearningObjective,
    Method,
    Misconception,
    ReviewItem,
    ReviewItemType,
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


def _ex_numbers(session: Session, chunk_ids) -> list[str]:
    out: list[str] = []
    for cid in chunk_ids or []:
        c = session.get(SourceChunk, cid)
        if c is not None and c.heading and c.heading.startswith("Zadanie "):
            out.append(c.heading.removeprefix("Zadanie ").rstrip(". "))
    return out


def knowledge_spec_view(session: Session, topic_id: int) -> KnowledgeSpecView | None:
    topic = session.get(Topic, topic_id)
    if topic is None:
        return None
    ke = session.scalars(
        select(KnowledgeExtraction).where(KnowledgeExtraction.topic_id == topic_id)
    ).one_or_none()

    items: list[KnowledgeItemView] = []
    counts: dict[str, int] = {}
    for kind, model in _KNOWLEDGE_KINDS:
        for obj in session.scalars(
            select(model).where(model.topic_id == topic_id).order_by(model.id)
        ):
            counts[kind] = counts.get(kind, 0) + 1
            title = getattr(obj, "name", None) or (getattr(obj, "statement", "") or "")[:80]
            detail = (
                getattr(obj, "description", None)
                or getattr(obj, "when_to_use", None)
                or getattr(obj, "worked_solution", None)
                or getattr(obj, "incorrect_reasoning", None)
            )
            prov = getattr(obj, "provenance", None)
            items.append(KnowledgeItemView(
                kind=kind, id=obj.id,
                status=obj.verification_status.value,
                title=title, detail=detail,
                evidence=getattr(obj, "explanation", None) or getattr(obj, "description", None),
                from_exercises=_ex_numbers(session, obj.source_chunk_ids),
                provenance=prov.value if prov is not None else None,
                distractor=getattr(obj, "distractor", None),
            ))

    flags = [
        f.detail for f in session.scalars(
            select(KnowledgeFlag).where(
                KnowledgeFlag.topic_id == topic_id, KnowledgeFlag.resolved.is_(False)
            ).order_by(KnowledgeFlag.id)
        )
    ]
    return KnowledgeSpecView(
        topic_id=topic_id,
        code=topic.official_requirement_code,
        name=topic.name,
        unit=f"{topic.unit.code} {topic.unit.name}" if topic.unit else None,
        requirement_text=topic.statement_latex or topic.description,
        extracted_at=ke.extracted_at if ke else None,
        prompt_version=ke.prompt_version if ke else None,
        model=ke.model if ke else None,
        exercises=ke.exercises if ke else 0,
        exported_at=ke.exported_at if ke else None,
        items=items, flags=flags, counts=counts,
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
