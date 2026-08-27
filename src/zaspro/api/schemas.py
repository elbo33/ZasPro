"""Pydantic response/request models for the API (SPEC §16: strict boundaries)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from zaspro.db.models import ReviewDecisionType, ReviewReasonCode


class TopicOption(BaseModel):
    topic_id: int
    code: str
    unit: str
    name: str


class MappingView(BaseModel):
    id: int
    source_chunk_id: int
    topic_id: int | None
    topic_code: str | None
    content_type: str
    difficulty: int | None
    confidence: float
    mapping_status: str
    rationale: str | None
    model: str | None
    prompt_version: str | None


class ReviewItemView(BaseModel):
    id: int
    item_type: str
    status: str
    risk: float
    confidence: float | None
    title: str
    topic_id: int | None
    source_document_id: int | None
    created_at: datetime
    audit_sample: bool = False  # queued for a spot-check, not because risky
    # context for the reviewer, one item per screen (SPEC §9)
    chunk_heading: str | None = None
    chunk_text: str | None = None
    chunk_latex: str | None = None
    mapping: MappingView | None = None
    candidates: list[TopicOption] = Field(default_factory=list)


class DecisionIn(BaseModel):
    reviewer: str
    decision: ReviewDecisionType
    reason_code: ReviewReasonCode | None = None
    note: str | None = None
    edit: dict | None = None


class BatchApproveIn(BaseModel):
    reviewer: str
    item_ids: list[int]


class BatchGroupView(BaseModel):
    topic_id: int | None
    source_document_id: int | None
    item_ids: list[int]
    min_confidence: float


class QueueStatsView(BaseModel):
    open_total: int
    by_type: dict[str, int]
    mappings_by_status: dict[str, int]
    unmapped_chunks: int
    batchable_groups: int


class DecisionResult(BaseModel):
    ok: bool
    stats: QueueStatsView
    next: ReviewItemView | None


class CurriculumTopic(BaseModel):
    id: int
    code: str | None
    name: str
    level: str
    parent_id: int | None
    mapped_chunks: int
    approved_chunks: int
    exercises: int


class CurriculumUnit(BaseModel):
    id: int
    code: str
    name: str
    topics: list[CurriculumTopic]


class SourceDocView(BaseModel):
    id: int
    file_ref: str
    session_code: str | None
    paper_version: str | None
    extraction_status: str
    page_count: int | None
    chunks: int
    exercises: int
    figures: int
    mappings_by_status: dict[str, int]


class SourceChunkView(BaseModel):
    id: int
    order_index: int
    heading: str | None
    content_type: str
    text: str
    confidence: float | None
    mapping: MappingView | None
