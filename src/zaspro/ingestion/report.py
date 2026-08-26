"""Post-ingestion completeness view."""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from zaspro.db.models import (
    Exercise,
    ExerciseFigure,
    Figure,
    RenderStatus,
    SourceChunk,
    SourceDocument,
)


@dataclass
class IngestionReport:
    document: str
    extraction_status: str
    chunks: int
    exercises: int
    parents: int
    leaf_tasks: int
    points_total: int
    figures_expected_tasks: int
    figures_rendered: int
    incomplete: list[str] = field(default_factory=list)

    @property
    def complete(self) -> bool:
        return not self.incomplete


def _rendered_figure_count(session: Session, exercise_id: int) -> int:
    return session.scalar(
        select(func.count())
        .select_from(ExerciseFigure)
        .join(Figure, Figure.id == ExerciseFigure.figure_id)
        .where(
            ExerciseFigure.exercise_id == exercise_id,
            Figure.render_status == RenderStatus.COMPLETE,
        )
    )


def build_report(session: Session, doc_id: int) -> IngestionReport:
    doc = session.get(SourceDocument, doc_id)
    if doc is None:
        raise ValueError(f"no source_document {doc_id}")

    exercises = session.scalars(
        select(Exercise).where(Exercise.source_document_id == doc_id)
    ).all()
    parents = [e for e in exercises if e.points_available is None]
    leaves = [e for e in exercises if e.points_available is not None]

    incomplete = [
        e.exercise_number
        for e in exercises
        if e.expected_figure_count > _rendered_figure_count(session, e.id)
    ]

    return IngestionReport(
        document=doc.file_ref,
        extraction_status=doc.extraction_status.value,
        chunks=session.scalar(
            select(func.count()).select_from(SourceChunk).where(
                SourceChunk.source_document_id == doc_id
            )
        ),
        exercises=len(exercises),
        parents=len(parents),
        leaf_tasks=len(leaves),
        points_total=sum(e.points_available or 0 for e in leaves),
        figures_expected_tasks=sum(1 for e in exercises if e.expected_figure_count),
        figures_rendered=session.scalar(
            select(func.count()).select_from(Figure).where(
                Figure.source_document_id == doc_id,
                Figure.render_status == RenderStatus.COMPLETE,
            )
        ),
        incomplete=sorted(incomplete, key=lambda n: [int(x) for x in n.split(".")]),
    )
