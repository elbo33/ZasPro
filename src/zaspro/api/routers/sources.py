"""Source-document pages (SPEC §17 dashboard skeleton). Read-only."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from zaspro.api.deps import get_db
from zaspro.api.schemas import SourceChunkView, SourceDocView
from zaspro.api.views import mapping_view
from zaspro.db.models import (
    ChunkMapping,
    Exercise,
    Figure,
    MappingStatus,
    SourceChunk,
    SourceDocument,
)


router = APIRouter(prefix="/sources", tags=["sources"])


def _status_counts(db: Session, doc_id: int) -> dict[str, int]:
    # primary mappings only — secondaries are always AI_SUGGESTED context
    counts = {s.value: 0 for s in MappingStatus}
    for status, n in db.execute(
        select(ChunkMapping.mapping_status, func.count())
        .join(SourceChunk, SourceChunk.id == ChunkMapping.source_chunk_id)
        .where(
            SourceChunk.source_document_id == doc_id,
            ChunkMapping.is_primary.is_(True),
        )
        .group_by(ChunkMapping.mapping_status)
    ):
        counts[status.value] = n
    return counts


@router.get("", response_model=list[SourceDocView])
def list_sources(db: Session = Depends(get_db)) -> list[SourceDocView]:
    docs = db.scalars(select(SourceDocument).order_by(SourceDocument.id)).all()
    out: list[SourceDocView] = []
    for d in docs:
        chunks = db.scalar(
            select(func.count()).select_from(SourceChunk).where(
                SourceChunk.source_document_id == d.id
            )
        ) or 0
        exercises = db.scalar(
            select(func.count()).select_from(Exercise).where(
                Exercise.source_document_id == d.id
            )
        ) or 0
        figures = db.scalar(
            select(func.count()).select_from(Figure).where(
                Figure.source_document_id == d.id
            )
        ) or 0
        out.append(
            SourceDocView(
                id=d.id,
                file_ref=d.file_ref,
                session_code=d.session_code,
                paper_version=d.paper_version,
                extraction_status=d.extraction_status.value,
                page_count=d.page_count,
                chunks=chunks,
                exercises=exercises,
                figures=figures,
                mappings_by_status=_status_counts(db, d.id),
            )
        )
    return out


@router.get("/{doc_id}/chunks", response_model=list[SourceChunkView])
def source_chunks(doc_id: int, db: Session = Depends(get_db)) -> list[SourceChunkView]:
    doc = db.get(SourceDocument, doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="source_document not found")
    chunks = db.scalars(
        select(SourceChunk)
        .where(SourceChunk.source_document_id == doc_id)
        .order_by(SourceChunk.order_index)
    ).all()
    out: list[SourceChunkView] = []
    for c in chunks:
        mapping = db.scalars(
            select(ChunkMapping).where(
                ChunkMapping.source_chunk_id == c.id,
                ChunkMapping.is_primary.is_(True),
            )
        ).one_or_none()
        out.append(
            SourceChunkView(
                id=c.id,
                order_index=c.order_index,
                heading=c.heading,
                content_type=c.content_type.value,
                text=c.text,
                confidence=c.confidence,
                mapping=mapping_view(db, mapping) if mapping else None,
            )
        )
    return out
