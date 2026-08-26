"""exercises + exercise_figures (SPEC §5).

M2 populates the extraction-time fields only: number, points, parent/subtask,
raw LaTeX, origin, provenance, and `expected_figure_count` from the DOCX
`<w:drawing>` count (M0.4). `topic_id` is NULL until M3 mapping;
`statement_latex_normalised`, `solution*`, `final_answer_repr`,
`verification_status` progress beyond DRAFT are M5.

A parent (subtask) exercise has `points_available` NULL and carries the shared
stem in `statement`; the stem is attached to each child at read time
(`full_statement`), never denormalised (SPEC §5).
"""

from __future__ import annotations

import enum
from typing import Any

from sqlalchemy import Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from zaspro.db.base import Base, TimestampMixin


class ExerciseOrigin(str, enum.Enum):
    OFFICIAL = "OFFICIAL"
    LICENSED = "LICENSED"
    OPEN = "OPEN"
    HUMAN_CREATED = "HUMAN_CREATED"
    AI_GENERATED = "AI_GENERATED"


class VerificationStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    AI_GENERATED = "AI_GENERATED"
    PENDING_REVIEW = "PENDING_REVIEW"
    AUTO_VERIFIED = "AUTO_VERIFIED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


def _enum(py_enum: type[enum.Enum], name: str) -> Enum:
    return Enum(py_enum, name=name, native_enum=False, validate_strings=True)


class Exercise(Base, TimestampMixin):
    __tablename__ = "exercises"
    __table_args__ = (
        UniqueConstraint("source_document_id", "exercise_number", name="uq_exercises_doc_number"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    # Provenance: which ingested document this came from (M2). topic_id (M3).
    source_document_id: Mapped[int | None] = mapped_column(
        ForeignKey("source_documents.id", ondelete="SET NULL")
    )
    topic_id: Mapped[int | None] = mapped_column(ForeignKey("topics.id", ondelete="SET NULL"))
    parent_exercise_id: Mapped[int | None] = mapped_column(
        ForeignKey("exercises.id", ondelete="CASCADE")
    )

    exercise_number: Mapped[str] = mapped_column(String(16))  # "7", "12", "12.1"
    statement: Mapped[str] = mapped_column(Text)
    statement_latex_raw: Mapped[str | None] = mapped_column(Text)
    statement_latex_normalised: Mapped[str | None] = mapped_column(Text)  # M5

    difficulty: Mapped[int | None] = mapped_column(Integer)
    exercise_type: Mapped[str | None] = mapped_column(String(64))
    solution: Mapped[str | None] = mapped_column(Text)
    solution_steps: Mapped[Any | None] = mapped_column(JSONB)
    final_answer_repr: Mapped[str | None] = mapped_column(Text)  # M5
    skills_required: Mapped[Any | None] = mapped_column(JSONB)

    origin: Mapped[ExerciseOrigin] = mapped_column(_enum(ExerciseOrigin, "exercise_origin"))
    verbatim_ok: Mapped[bool] = mapped_column(default=False)
    variant_group_id: Mapped[str | None] = mapped_column(String(64))
    points_available: Mapped[int | None] = mapped_column(Integer)  # NULL for a parent
    # <w:drawing> elements in this task's DOCX range (M0.4). incomplete if it
    # exceeds the number of linked, rendered figures.
    expected_figure_count: Mapped[int] = mapped_column(Integer, default=0)

    verification_status: Mapped[VerificationStatus] = mapped_column(
        _enum(VerificationStatus, "verification_status"), default=VerificationStatus.DRAFT
    )

    parent: Mapped[Exercise | None] = relationship(
        back_populates="subtasks", remote_side="Exercise.id"
    )
    subtasks: Mapped[list[Exercise]] = relationship(
        back_populates="parent", cascade="all, delete-orphan"
    )
    figures: Mapped[list["Figure"]] = relationship(  # noqa: F821
        secondary="exercise_figures", backref="exercises"
    )

    @property
    def full_statement(self) -> str:
        """Stem (from the parent) + this exercise's own statement."""

        if self.parent is not None and self.parent.statement:
            return f"{self.parent.statement}\n\n{self.statement}"
        return self.statement


class ExerciseFigure(Base):
    __tablename__ = "exercise_figures"

    exercise_id: Mapped[int] = mapped_column(
        ForeignKey("exercises.id", ondelete="CASCADE"), primary_key=True
    )
    figure_id: Mapped[int] = mapped_column(
        ForeignKey("figures.id", ondelete="CASCADE"), primary_key=True
    )
