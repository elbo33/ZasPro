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
    topic_name: str | None = None
    is_primary: bool = True
    content_type: str
    difficulty: int | None
    confidence: float
    mapping_status: str
    rationale: str | None
    model: str | None
    prompt_version: str | None


class KnowledgeItemView(BaseModel):
    kind: str            # concept | formula | method | example | objective | misconception
    id: int
    status: str          # VerificationStatus
    title: str           # name / statement head
    detail: str | None = None
    extra: str | None = None  # explanation / correction / conditions


class KnowledgeSpecView(BaseModel):
    section_id: int
    slug: str
    name: str
    scope: str | None = None
    requirement_codes: list[str] = Field(default_factory=list)
    written_at: datetime | None = None
    prompt_version: str | None = None
    model: str | None = None
    exported_at: datetime | None = None
    items: list[KnowledgeItemView] = Field(default_factory=list)
    counts: dict[str, int] = Field(default_factory=dict)


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
    chunk_stem: str | None = None  # the parent task's shared statement, for a subtask
    mapping: MappingView | None = None  # the primary
    secondaries: list[MappingView] = Field(default_factory=list)
    candidates: list[TopicOption] = Field(default_factory=list)
    knowledge: KnowledgeSpecView | None = None  # for a KNOWLEDGE_SPEC card


class KnowledgeIndexRow(BaseModel):
    section_id: int
    slug: str
    name: str
    order_index: int
    requirement_codes: list[str] = Field(default_factory=list)
    counts: dict[str, int] = Field(default_factory=dict)
    review_status: str | None = None  # OPEN | APPROVED | REJECTED | None (not written)
    review_item_id: int | None = None
    exported_at: datetime | None = None
    prompt_version: str | None = None


class ExportResult(BaseModel):
    ok: bool
    slug: str
    path: str | None = None
    error: str | None = None


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
    mapped_chunks: int  # chunks whose PRIMARY requirement is this topic
    also_tests: int = 0  # chunks that name this topic only as a secondary
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
