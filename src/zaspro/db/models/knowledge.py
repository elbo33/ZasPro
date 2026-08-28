"""Knowledge tables (SPEC §5 "Knowledge").

One row per extracted item. Every topic gets a COMPLETE spec (ADR 0011 §2):
the agent uses exam exercises where they inform an item and its own knowledge
of the subject where they do not. `provenance` records which — as information
for the reviewer, not a gate. `source_chunk_ids` holds the backing chunks for
exam-derived items. The human approves every spec in the dashboard; that is the
verification step.

`verification_status` reuses `zaspro.db.models.exercises.VerificationStatus`.
"""

from __future__ import annotations

import enum
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from zaspro.db.base import Base, TimestampMixin
from zaspro.db.models.exercises import VerificationStatus


def _vs() -> Enum:
    return Enum(
        VerificationStatus, name="verification_status",
        native_enum=False, validate_strings=True,
    )


class KnowledgeProvenance(str, enum.Enum):
    """Where a knowledge item came from — recorded on every item, for every
    kind (concept / formula / method / example / objective / misconception).
    Information for the reviewer, never a gate: a topic with no exam material
    is legitimately `AGENT_KNOWLEDGE` throughout."""

    EXAM_TASK = "EXAM_TASK"              # from one or more exam exercises
    MARKING_SCHEME = "MARKING_SCHEME"    # from a Zasady oceniania block
    DISTRACTOR = "DISTRACTOR"            # from a specific multiple-choice distractor
    INFORMATOR = "INFORMATOR"            # CKE informator commentary (not ingested yet)
    AGENT_KNOWLEDGE = "AGENT_KNOWLEDGE"  # the model's own knowledge of the subject


class FlagKind(str, enum.Enum):
    CONFLICT = "CONFLICT"  # sources disagree; both readings kept
    GAP = "GAP"            # kept for back-compat; the agent no longer emits GAPs


def _prov() -> Enum:
    return Enum(
        KnowledgeProvenance, name="knowledge_provenance",
        native_enum=False, validate_strings=True, length=32,
    )


class _KItem:
    """Mixin: every knowledge item is tied to a topic, carries its provenance,
    and (for exam-derived items) the backing source chunks."""

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    topic_id: Mapped[int] = mapped_column(
        ForeignKey("topics.id", ondelete="CASCADE"), index=True
    )
    source_chunk_ids: Mapped[Any] = mapped_column(JSONB, default=list)
    provenance: Mapped[KnowledgeProvenance] = mapped_column(
        _prov(), default=KnowledgeProvenance.AGENT_KNOWLEDGE,
        server_default=KnowledgeProvenance.AGENT_KNOWLEDGE.value,
    )
    verification_status: Mapped[VerificationStatus] = mapped_column(
        _vs(), default=VerificationStatus.AI_GENERATED
    )


class Concept(Base, TimestampMixin, _KItem):
    __tablename__ = "concepts"
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    explanation: Mapped[str | None] = mapped_column(Text)
    difficulty: Mapped[int | None] = mapped_column(Integer)
    order_index: Mapped[int] = mapped_column(Integer, default=0)


class Formula(Base, TimestampMixin, _KItem):
    __tablename__ = "formulas"
    name: Mapped[str] = mapped_column(String(255))
    latex_raw: Mapped[str] = mapped_column(Text)
    latex_normalised: Mapped[str | None] = mapped_column(Text)  # M5
    description: Mapped[str | None] = mapped_column(Text)
    conditions: Mapped[str | None] = mapped_column(Text)
    order_index: Mapped[int] = mapped_column(Integer, default=0)


class Method(Base, TimestampMixin, _KItem):
    __tablename__ = "methods"
    name: Mapped[str] = mapped_column(String(255))
    when_to_use: Mapped[str | None] = mapped_column(Text)
    steps: Mapped[Any | None] = mapped_column(JSONB)  # list[str]
    order_index: Mapped[int] = mapped_column(Integer, default=0)


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
    # when provenance == DISTRACTOR: the named option(s) the error was read off,
    # e.g. "B and D" or "C: 20000 · 1,06" (the exercise is in source_chunk_ids)
    distractor: Mapped[str | None] = mapped_column(String(255))


class LearningObjective(Base, TimestampMixin, _KItem):
    __tablename__ = "learning_objectives"
    statement: Mapped[str] = mapped_column(Text)
    bloom_level: Mapped[str | None] = mapped_column(String(32))
    order_index: Mapped[int] = mapped_column(Integer, default=0)


class KnowledgeFlag(Base, TimestampMixin):
    """A CONFLICT the agent surfaced during extraction (sources disagree, both
    readings kept). GAPs are no longer emitted — every topic gets a full spec."""

    __tablename__ = "knowledge_flags"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    topic_id: Mapped[int] = mapped_column(
        ForeignKey("topics.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[FlagKind] = mapped_column(
        Enum(FlagKind, name="flag_kind", native_enum=False, validate_strings=True)
    )
    item_kind: Mapped[str] = mapped_column(String(32))  # concept | formula | …
    detail: Mapped[str] = mapped_column(Text)
    source_chunk_ids: Mapped[Any] = mapped_column(JSONB, default=list)
    resolved: Mapped[bool] = mapped_column(default=False)


class KnowledgeExtraction(Base, TimestampMixin):
    """One row per topic: the state of its knowledge layer — last extraction,
    the review item guarding it, and whether it has been approved and frozen to
    a committed git file (ADR 0011). The database stays the working store; the
    exported YAML under `knowledge/topics/<code>.yaml` is the record of truth.
    This table is itself rebuildable from those files plus the job history."""

    __tablename__ = "knowledge_extractions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    topic_id: Mapped[int] = mapped_column(
        ForeignKey("topics.id", ondelete="CASCADE"), unique=True, index=True
    )
    agent_name: Mapped[str] = mapped_column(String(32))
    model: Mapped[str | None] = mapped_column(String(64))
    prompt_version: Mapped[str] = mapped_column(String(32))
    exercises: Mapped[int] = mapped_column(Integer, default=0)  # touch-set size at extraction
    extracted_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # the KNOWLEDGE_SPEC review item that gates approval (one card per topic)
    review_item_id: Mapped[int | None] = mapped_column(
        ForeignKey("review_items.id", ondelete="SET NULL")
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime)
    approved_by: Mapped[str | None] = mapped_column(String(120))
    exported_at: Mapped[datetime | None] = mapped_column(DateTime)
    export_path: Mapped[str | None] = mapped_column(String(255))
