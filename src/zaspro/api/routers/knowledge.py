"""Knowledge-layer endpoints (M4, ADR 0012).

`GET /knowledge` — the section index for the dashboard's Knowledge page.
`GET /knowledge/{section_id}` — the full spec (same shape the review card uses).
`POST /knowledge/{section_id}/export` — write the committed YAML once the review
card is resolved.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from zaspro.api.deps import get_db
from zaspro.api.schemas import ExportResult, KnowledgeIndexRow, KnowledgeSpecView
from zaspro.api.views import knowledge_spec_view
from zaspro.db.models import (
    ReviewItem, ReviewItemType, Section, SectionSpec, Topic,
)
from zaspro.knowledge.export import ExportError, export_section

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.get("", response_model=list[KnowledgeIndexRow])
def get_index(db: Session = Depends(get_db)) -> list[KnowledgeIndexRow]:
    sections = db.scalars(select(Section).order_by(Section.order_index)).all()
    specs = {s.section_id: s for s in db.scalars(select(SectionSpec))}
    ris = {
        r.ref_id: r
        for r in db.scalars(
            select(ReviewItem).where(
                ReviewItem.item_type == ReviewItemType.KNOWLEDGE_SPEC,
                ReviewItem.ref_table == "sections",
            )
        )
    }
    rows: list[KnowledgeIndexRow] = []
    for sec in sections:
        spec = knowledge_spec_view(db, sec.id)
        sp = specs.get(sec.id)
        ri = ris.get(sec.id)
        codes = sorted(
            db.get(Topic, sr.topic_id).official_requirement_code
            for sr in sec.requirements
        )
        rows.append(KnowledgeIndexRow(
            section_id=sec.id,
            slug=sec.slug,
            name=sec.name,
            order_index=sec.order_index,
            requirement_codes=codes,
            counts=spec.counts if spec else {},
            review_status=ri.status.value if ri else None,
            review_item_id=ri.id if ri else None,
            exported_at=sp.exported_at if sp else None,
            prompt_version=sp.prompt_version if sp else None,
        ))
    return rows


@router.get("/{section_id}", response_model=KnowledgeSpecView)
def get_spec(section_id: int, db: Session = Depends(get_db)) -> KnowledgeSpecView:
    spec = knowledge_spec_view(db, section_id)
    if spec is None:
        raise HTTPException(status_code=404, detail=f"section {section_id} not found")
    return spec


@router.post("/{section_id}/export", response_model=ExportResult)
def post_export(
    section_id: int, reviewer: str = "reviewer", db: Session = Depends(get_db)
) -> ExportResult:
    section = db.get(Section, section_id)
    slug = section.slug if section else str(section_id)
    try:
        path = export_section(db, section_id, reviewer=reviewer)
    except ExportError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    return ExportResult(ok=True, slug=slug, path=str(path))
