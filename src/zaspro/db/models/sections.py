"""Teaching sections (M4) — the teaching layer above the requirements.

A `Section` is a lesson-sized teaching unit. It covers one or more
`topics.official_requirement_code`s via `section_requirements`; together the
sections cover every podstawowy requirement exactly once (asserted at seed
time). Sections — not requirements — are the unit the Knowledge Agent writes a
spec for (ADR 0012). Seeded from `seeds/teaching_sections.yaml`.
"""

from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from zaspro.db.base import Base, Slug, TimestampMixin


class Section(Base, TimestampMixin):
    __tablename__ = "sections"
    __table_args__ = (
        UniqueConstraint("subject_id", "order_index", name="uq_sections_subject_order"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id", ondelete="CASCADE"))
    slug: Mapped[Slug] = mapped_column(unique=True)
    name: Mapped[str] = mapped_column(Text)
    scope: Mapped[str] = mapped_column(Text)  # bounds what the spec should contain
    order_index: Mapped[int] = mapped_column(Integer)

    requirements: Mapped[list["SectionRequirement"]] = relationship(
        back_populates="section", cascade="all, delete-orphan",
        order_by="SectionRequirement.topic_id",
    )


class SectionRequirement(Base):
    """One (section -> requirement) link. A requirement belongs to exactly one
    section; a section covers one or more."""

    __tablename__ = "section_requirements"
    section_id: Mapped[int] = mapped_column(
        ForeignKey("sections.id", ondelete="CASCADE"), primary_key=True
    )
    topic_id: Mapped[int] = mapped_column(
        ForeignKey("topics.id", ondelete="CASCADE"), primary_key=True, index=True
    )

    section: Mapped[Section] = relationship(back_populates="requirements")
