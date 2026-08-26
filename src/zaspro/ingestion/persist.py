"""Write an IngestionResult to the database.

Provenance is preserved: every chunk and exercise is tied to its
`source_document`, keeps its order, and records `extraction_method =
pandoc_omml` with `confidence = NULL` (deterministic).
"""

from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from zaspro.db.models import (
    ContentType,
    Exercise,
    ExerciseOrigin,
    ExtractionMethod,
    ExtractionStatus,
    Source,
    SourceChunk,
    SourceDocument,
    VerificationStatus,
)
from zaspro.ingestion.pipeline import IngestionResult

_MMAP = re.compile(r"MMAP-([PR]0)-(\d{3})-([AB])-(\d{4})-")
_MATH_DELIM = re.compile(r"\\[()\[\]]")


def _plain(latex: str) -> str:
    """A readable plain-text rendering of a LaTeX fragment for `text` columns.
    The raw LaTeX stays authoritative in `latex` / `statement_latex_raw`."""

    s = _MATH_DELIM.sub("", latex)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _doc_metadata(file_ref: str) -> dict[str, str | None]:
    m = _MMAP.search(file_ref)
    if not m:
        return {"level_code": None, "variant_code": None, "paper_version": None, "session_code": None}
    level_code, variant, paper, session = m.groups()
    return {
        "level_code": level_code,
        "variant_code": variant,
        "paper_version": paper,
        "session_code": session,
    }


def persist_ingestion(session: Session, result: IngestionResult) -> SourceDocument:
    source = session.scalars(
        select(Source).where(Source.file_ref == result.source_file)
    ).one()
    meta = _doc_metadata(result.source_file)
    sibling = None
    if meta["variant_code"] == "660":
        sibling = result.source_file.replace("-660-", "-100-").replace(".docx", ".pdf")

    doc = session.scalars(
        select(SourceDocument).where(SourceDocument.file_ref == result.source_file)
    ).one_or_none()
    if doc is None:
        doc = SourceDocument(source_id=source.id, file_ref=result.source_file)
        session.add(doc)
    doc.variant_code = meta["variant_code"]
    doc.paper_version = meta["paper_version"]
    doc.session_code = meta["session_code"]
    doc.sibling_docx_ref = sibling
    doc.extraction_status = ExtractionStatus.SEGMENTED
    session.flush()

    # Reingest cleanly: drop prior chunks/exercises for this document.
    for ex in session.scalars(select(Exercise).where(Exercise.source_document_id == doc.id)):
        session.delete(ex)
    for ch in session.scalars(select(SourceChunk).where(SourceChunk.source_document_id == doc.id)):
        session.delete(ch)
    session.flush()

    group_prefix = f"{meta['session_code']}-{meta['level_code']}" if meta["session_code"] else None
    by_number: dict[str, Exercise] = {}

    for chunk in result.chunks:
        session.add(
            SourceChunk(
                source_document_id=doc.id,
                heading=f"Zadanie {chunk.exercise_number}.",
                section=chunk.parent_number or chunk.exercise_number,
                content_type=ContentType.EXERCISE,
                text=_plain(chunk.statement_latex_raw),
                latex=chunk.statement_latex_raw,
                order_index=chunk.order_index,
                extraction_method=ExtractionMethod.pandoc_omml,
                confidence=None,  # deterministic
            )
        )
        ex = Exercise(
            source_document_id=doc.id,
            exercise_number=chunk.exercise_number,
            statement=_plain(chunk.statement_latex_raw),
            statement_latex_raw=chunk.statement_latex_raw,
            origin=ExerciseOrigin.OFFICIAL,
            verbatim_ok=source.verbatim_ok,
            variant_group_id=(
                f"{group_prefix}-{chunk.exercise_number}" if group_prefix else None
            ),
            points_available=chunk.points_available,
            expected_figure_count=chunk.expected_figure_count,
            verification_status=VerificationStatus.DRAFT,
        )
        session.add(ex)
        session.flush()
        by_number[chunk.exercise_number] = ex

    # second pass: link subtasks to their parent
    for chunk in result.chunks:
        if chunk.parent_number:
            child = by_number[chunk.exercise_number]
            child.parent_exercise_id = by_number[chunk.parent_number].id
    session.flush()

    doc.extraction_status = ExtractionStatus.VALIDATED
    session.flush()
    return doc
