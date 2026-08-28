"""Knowledge tables (SPEC §5 "Knowledge") — one spec per teaching section.

The Knowledge Agent writes each section as a textbook chapter would (ADR 0012):
concepts, formulas with conditions, methods with when-to-use, worked examples
that build in difficulty, learning objectives, and the mistakes students make.
Written from subject knowledge, scoped by the section's requirement codes.
Exercises are not involved — no source references, no provenance labels.

The human approves every section spec in the dashboard; that is the only
verification. `verification_status` reuses
`zaspro.db.models.exercises.VerificationStatus`.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from zaspro.db.base import Base, TimestampMixin
from zaspro.db.models.exercises import VerificationStatus


def _vs() -> Enum:
    return Enum(
        VerificationStatus, name="verification_status",
        native_enum=False, validate_strings=True,
    )


class _KItem:
    """Mixin: every knowledge item belongs to one section and carries a
    verification status the reviewer sets on the section card."""

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    section_id: Mapped[int] = mapped_column(
        ForeignKey("sections.id", ondelete="CASCADE"), index=True
    )
    verification_status: Mapped[VerificationStatus] = mapped_column(
        _vs(), default=VerificationStatus.AI_GENERATED
    )
    order_index: Mapped[int] = mapped_column(Integer, default=0)


class Concept(Base, TimestampMixin, _KItem):
    __tablename__ = "concepts"
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)   # the definition
    explanation: Mapped[str | None] = mapped_column(Text)   # elaboration / why it matters
    difficulty: Mapped[int | None] = mapped_column(Integer)


class Formula(Base, TimestampMixin, _KItem):
    __tablename__ = "formulas"
    name: Mapped[str] = mapped_column(String(255))
    latex_raw: Mapped[str] = mapped_column(Text)
    latex_normalised: Mapped[str | None] = mapped_column(Text)  # M5
    description: Mapped[str | None] = mapped_column(Text)
    conditions: Mapped[str | None] = mapped_column(Text)


class Method(Base, TimestampMixin, _KItem):
    __tablename__ = "methods"
    name: Mapped[str] = mapped_column(String(255))
    when_to_use: Mapped[str | None] = mapped_column(Text)
    steps: Mapped[Any | None] = mapped_column(JSONB)  # list[str]


class Example(Base, TimestampMixin, _KItem):
    __tablename__ = "examples"
    concept_id: Mapped[int | None] = mapped_column(
        ForeignKey("concepts.id", ondelete="SET NULL")
    )
    statement: Mapped[str] = mapped_column(Text)
    worked_solution: Mapped[str | None] = mapped_column(Text)
    difficulty: Mapped[int | None] = mapped_column(Integer)


class Misconception(Base, TimestampMixin, _KItem):
    __tablename__ = "misconceptions"
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    incorrect_reasoning: Mapped[str | None] = mapped_column(Text)
    correct_reasoning: Mapped[str | None] = mapped_column(Text)
    example: Mapped[str | None] = mapped_column(Text)
    severity: Mapped[int | None] = mapped_column(Integer)  # 1..5


class LearningObjective(Base, TimestampMixin, _KItem):
    __tablename__ = "learning_objectives"
    statement: Mapped[str] = mapped_column(Text)
    bloom_level: Mapped[str | None] = mapped_column(String(32))


class SectionSpec(Base, TimestampMixin):
    """One row per section: the state of its knowledge spec — last write, the
    review card guarding it, and whether it has been approved and frozen to a
    committed git file (ADR 0012). The DB is the working store; the exported
    YAML under `knowledge/sections/<slug>.yaml` is the record."""

    __tablename__ = "section_specs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    section_id: Mapped[int] = mapped_column(
        ForeignKey("sections.id", ondelete="CASCADE"), unique=True, index=True
    )
    agent_name: Mapped[str] = mapped_column(String(32))
    model: Mapped[str | None] = mapped_column(String(64))
    prompt_version: Mapped[str] = mapped_column(String(32))
    written_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    review_item_id: Mapped[int | None] = mapped_column(
        ForeignKey("review_items.id", ondelete="SET NULL")
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime)
    approved_by: Mapped[str | None] = mapped_column(String(120))
    exported_at: Mapped[datetime | None] = mapped_column(DateTime)
    export_path: Mapped[str | None] = mapped_column(String(255))
