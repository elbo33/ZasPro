"""Post-ingestion completeness view.

Two figure quantities that are NOT the same and must never be shown as if they
were:

* **figure regions** — distinct `<w:drawing>` figures a document contains
  (`exercises.own_figure_count > 0`). Each yields one `Figure` row.
* **figure-bearing exercises** — exercises that need a figure attached, which is
  the regions *plus* the subtasks that inherit their parent's figure
  (`exercises.expected_figure_count > 0`).

`regions_expected == regions_rendered` and `incomplete == []` together mean the
figure work is done.
"""

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

    figure_regions_expected: int  # exercises.own_figure_count > 0
    figure_regions_rendered: int  # Figure rows, render_status = COMPLETE
    figure_bearing_exercises: int  # exercises.expected_figure_count > 0
    incomplete: list[str] = field(default_factory=list)  # expected > linked-and-complete

    @property
    def figures_ok(self) -> bool:
        return (
            self.figure_regions_rendered == self.figure_regions_expected
            and not self.incomplete
        )

    @property
    def complete(self) -> bool:
        return self.figures_ok and self.extraction_status == "validated"


def _linked_complete(session: Session, exercise_id: int) -> int:
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

    incomplete = sorted(
        (
            e.exercise_number
            for e in exercises
            if e.expected_figure_count > _linked_complete(session, e.id)
        ),
        key=lambda n: [int(x) for x in n.split(".")],
    )

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
        figure_regions_expected=sum(1 for e in exercises if e.own_figure_count > 0),
        figure_regions_rendered=session.scalar(
            select(func.count()).select_from(Figure).where(
                Figure.source_document_id == doc_id,
                Figure.render_status == RenderStatus.COMPLETE,
            )
        ),
        figure_bearing_exercises=sum(1 for e in exercises if e.expected_figure_count > 0),
        incomplete=incomplete,
    )
