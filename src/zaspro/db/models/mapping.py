"""Curriculum mapping (SPEC §10) and the review queue (SPEC §9).

`chunk_mappings.confidence` is the **mapping** agent's confidence — a different
thing from `source_chunks.confidence` (extraction). A deterministically
extracted chunk (extraction confidence NULL) still gets a mapping confidence,
and only a *low* mapping confidence puts an item in the review queue. That is
what keeps deterministic chunks from cluttering it (SPEC §9).
"""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from zaspro.db.base import Base, TimestampMixin
from zaspro.db.models.ingestion import ContentType


class MappingStatus(str, enum.Enum):
    AI_SUGGESTED = "AI_SUGGESTED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class ReviewItemType(str, enum.Enum):
    CURRICULUM_MAPPING = "CURRICULUM_MAPPING"
    FORMULA = "FORMULA"
    EXERCISE = "EXERCISE"
    MISCONCEPTION = "MISCONCEPTION"
    MERGE_CANDIDATE = "MERGE_CANDIDATE"
    EXTRACTION_CONFLICT = "EXTRACTION_CONFLICT"
    NORMALISATION_FAILURE = "NORMALISATION_FAILURE"


class ReviewStatus(str, enum.Enum):
    OPEN = "OPEN"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class ReviewDecisionType(str, enum.Enum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    EDIT = "EDIT"


class ReviewReasonCode(str, enum.Enum):
    WRONG_TOPIC = "WRONG_TOPIC"
    WRONG_CONTENT_TYPE = "WRONG_CONTENT_TYPE"
    NOT_CURRICULUM = "NOT_CURRICULUM"
    AMBIGUOUS = "AMBIGUOUS"
    LOW_QUALITY_SOURCE = "LOW_QUALITY_SOURCE"
    OTHER = "OTHER"


def _enum(py_enum: type[enum.Enum], name: str) -> Enum:
    return Enum(py_enum, name=name, native_enum=False, validate_strings=True)


class ChunkMapping(Base, TimestampMixin):
    __tablename__ = "chunk_mappings"
    __table_args__ = (UniqueConstraint("source_chunk_id", name="uq_chunk_mappings_chunk"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    source_chunk_id: Mapped[int] = mapped_column(
        ForeignKey("source_chunks.id", ondelete="CASCADE")
    )
    topic_id: Mapped[int | None] = mapped_column(ForeignKey("topics.id", ondelete="SET NULL"))

    content_type: Mapped[ContentType] = mapped_column(_enum(ContentType, "content_type"))
    difficulty: Mapped[int | None] = mapped_column(Integer)
    confidence: Mapped[float] = mapped_column(Float)  # mapping confidence, always set
    mapping_status: Mapped[MappingStatus] = mapped_column(
        _enum(MappingStatus, "mapping_status"), default=MappingStatus.AI_SUGGESTED
    )
    rationale: Mapped[str | None] = mapped_column(Text)
    model: Mapped[str | None] = mapped_column(String(64))
    prompt_version: Mapped[str | None] = mapped_column(String(32))


class ReviewItem(Base):
    __tablename__ = "review_items"
    __table_args__ = (
        UniqueConstraint("item_type", "ref_table", "ref_id", name="uq_review_items_ref"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    item_type: Mapped[ReviewItemType] = mapped_column(_enum(ReviewItemType, "review_item_type"))
    ref_table: Mapped[str] = mapped_column(String(64))
    ref_id: Mapped[int] = mapped_column(Integer)

    status: Mapped[ReviewStatus] = mapped_column(
        _enum(ReviewStatus, "review_status"), default=ReviewStatus.OPEN, index=True
    )
    # higher = show first. 1 - confidence, nudged by item type.
    risk: Mapped[float] = mapped_column(Float, index=True)
    confidence: Mapped[float | None] = mapped_column(Float)
    title: Mapped[str] = mapped_column(Text)

    # for "batch approval for items sharing high confidence and the same topic
    # and source" (SPEC §9)
    topic_id: Mapped[int | None] = mapped_column(ForeignKey("topics.id", ondelete="SET NULL"))
    source_document_id: Mapped[int | None] = mapped_column(
        ForeignKey("source_documents.id", ondelete="SET NULL")
    )

    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    resolved_at: Mapped[datetime | None] = mapped_column()

    decisions: Mapped[list[ReviewDecision]] = relationship(
        back_populates="item", cascade="all, delete-orphan", order_by="ReviewDecision.id"
    )


class ReviewDecision(Base):
    __tablename__ = "review_decisions"
    __table_args__ = (
        # a rejection must carry a reason code — the training signal (SPEC §9)
        CheckConstraint(
            "decision <> 'REJECT' OR reason_code IS NOT NULL",
            name="ck_review_decisions_reject_needs_reason",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    review_item_id: Mapped[int] = mapped_column(
        ForeignKey("review_items.id", ondelete="CASCADE")
    )
    reviewer: Mapped[str] = mapped_column(String(120))
    decision: Mapped[ReviewDecisionType] = mapped_column(
        _enum(ReviewDecisionType, "review_decision_type")
    )
    reason_code: Mapped[ReviewReasonCode | None] = mapped_column(
        _enum(ReviewReasonCode, "review_reason_code")
    )
    prior_status: Mapped[str] = mapped_column(String(32))
    note: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    item: Mapped[ReviewItem] = relationship(back_populates="decisions")
