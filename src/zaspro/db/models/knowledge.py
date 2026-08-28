"""Knowledge tables (SPEC §5 "Knowledge", §11).

One row per extracted item, each carrying `source_chunk_ids` — the chunks the
Knowledge Agent drew it from (SPEC §11: "every extracted item carries source
chunk references"; the agent may not invent facts absent from the chunks).
Conflicts and gaps are `knowledge_flags` rows and become review items.

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


class MisconceptionSource(str, enum.Enum):
    """Where a misconception actually came from (SPEC §11 provenance). The yield
    check keys on this: mostly `AGENT_INFERENCE` / `UNSOURCED` means it is the
    model's priors about student errors, not a database."""

    MARKING_SCHEME = "MARKING_SCHEME"      # a partial-credit / "0 pkt jeśli…" rule
    INFORMATOR = "INFORMATOR"              # CKE informator commentary
    DISTRACTOR_INFERENCE = "DISTRACTOR_INFERENCE"  # a named multiple-choice distractor built to catch this error
    AGENT_INFERENCE = "AGENT_INFERENCE"    # inferred from an exercise's structure
    UNSOURCED = "UNSOURCED"                # no chunk supports it — a §11 violation


class FlagKind(str, enum.Enum):
    CONFLICT = "CONFLICT"  # sources disagree; both readings kept
    GAP = "GAP"            # information missing for this topic


class _KItem:
    """Mixin: every knowledge item is tied to a topic and its source chunks."""

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    topic_id: Mapped[int] = mapped_column(
        ForeignKey("topics.id", ondelete="CASCADE"), index=True
    )
    source_chunk_ids: Mapped[Any] = mapped_column(JSONB, default=list)
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
    source_kind: Mapped[MisconceptionSource] = mapped_column(
        Enum(MisconceptionSource, name="misconception_source",
             native_enum=False, validate_strings=True, length=32)
    )
    # for DISTRACTOR_INFERENCE: the named distractor(s) the error was read off,
    # e.g. "B and D" or "C: 20000 · 1,06" (the exercise is in source_chunk_ids)
    distractor: Mapped[str | None] = mapped_column(String(255))


class LearningObjective(Base, TimestampMixin, _KItem):
    __tablename__ = "learning_objectives"
    statement: Mapped[str] = mapped_column(Text)
    bloom_level: Mapped[str | None] = mapped_column(String(32))
    order_index: Mapped[int] = mapped_column(Integer, default=0)


class KnowledgeFlag(Base, TimestampMixin):
    """A conflict or gap surfaced during extraction (SPEC §11) — a review item."""

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
