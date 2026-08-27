"""The single review queue (SPEC §9).

One queue, typed items, sorted so the doubtful things surface first
(`risk` desc). Deterministically extracted content never lands here on its own —
only an uncertain downstream *mapping* does (SPEC §9, §10). Every decision is
appended immutably with reviewer, timestamp and prior status; a rejection
carries a reason code (the DB enforces it too).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from zaspro.db.models import (
    ChunkMapping,
    MappingStatus,
    ReviewDecision,
    ReviewDecisionType,
    ReviewItem,
    ReviewItemType,
    ReviewReasonCode,
    ReviewStatus,
    SourceChunk,
)
from zaspro.mapping.handler import apply_mapping_to_exercise

# batch approval is only offered above this (SPEC §9: "sharing high confidence")
BATCH_MIN_CONFIDENCE = 0.6


class ReviewError(RuntimeError):
    pass


@dataclass
class QueueStats:
    open_total: int
    by_type: dict[str, int]
    mappings_by_status: dict[str, int]
    unmapped_chunks: int  # chunks with no mapping row at all (SPEC §10 count)
    batchable_groups: int


@dataclass
class BatchGroup:
    topic_id: int | None
    source_document_id: int | None
    item_ids: list[int] = field(default_factory=list)
    min_confidence: float = 1.0


def _now() -> datetime:
    return datetime.now(timezone.utc)


def next_item(session: Session, *, exclude_ids: set[int] | None = None) -> ReviewItem | None:
    """Highest-risk OPEN item. `exclude_ids` lets the UI page forward through the
    queue ("skip") without those items being resolved."""

    stmt = (
        select(ReviewItem)
        .where(ReviewItem.status == ReviewStatus.OPEN)
        .order_by(ReviewItem.risk.desc(), ReviewItem.id)
        .limit(1)
    )
    if exclude_ids:
        stmt = stmt.where(ReviewItem.id.not_in(exclude_ids))
    return session.scalars(stmt).first()


def queue_stats(session: Session) -> QueueStats:
    open_total = session.scalar(
        select(func.count()).select_from(ReviewItem).where(ReviewItem.status == ReviewStatus.OPEN)
    ) or 0

    by_type = {t.value: 0 for t in ReviewItemType}
    for item_type, n in session.execute(
        select(ReviewItem.item_type, func.count())
        .where(ReviewItem.status == ReviewStatus.OPEN)
        .group_by(ReviewItem.item_type)
    ):
        by_type[item_type.value] = n

    mappings_by_status = {s.value: 0 for s in MappingStatus}
    for status, n in session.execute(
        select(ChunkMapping.mapping_status, func.count()).group_by(ChunkMapping.mapping_status)
    ):
        mappings_by_status[status.value] = n

    unmapped_chunks = session.scalar(
        select(func.count())
        .select_from(SourceChunk)
        .outerjoin(ChunkMapping, ChunkMapping.source_chunk_id == SourceChunk.id)
        .where(ChunkMapping.id.is_(None))
    ) or 0

    return QueueStats(
        open_total=open_total,
        by_type=by_type,
        mappings_by_status=mappings_by_status,
        unmapped_chunks=unmapped_chunks,
        batchable_groups=len(batch_groups(session)),
    )


def batch_groups(session: Session) -> list[BatchGroup]:
    """OPEN CURRICULUM_MAPPING items that share a topic and a source document and
    are all confident enough — the "batch approve" affordance (SPEC §9)."""

    rows = session.execute(
        select(ReviewItem.id, ReviewItem.topic_id, ReviewItem.source_document_id, ReviewItem.confidence)
        .where(
            ReviewItem.status == ReviewStatus.OPEN,
            ReviewItem.item_type == ReviewItemType.CURRICULUM_MAPPING,
            ReviewItem.topic_id.is_not(None),
            ReviewItem.confidence >= BATCH_MIN_CONFIDENCE,
        )
        .order_by(ReviewItem.topic_id, ReviewItem.source_document_id, ReviewItem.id)
    ).all()

    groups: dict[tuple[int | None, int | None], BatchGroup] = {}
    for item_id, topic_id, doc_id, conf in rows:
        key = (topic_id, doc_id)
        g = groups.setdefault(key, BatchGroup(topic_id=topic_id, source_document_id=doc_id))
        g.item_ids.append(item_id)
        g.min_confidence = min(g.min_confidence, conf if conf is not None else 1.0)
    return [g for g in groups.values() if len(g.item_ids) >= 2]


def _resolve_mapping(session: Session, item: ReviewItem, decision: ReviewDecisionType,
                     edit: dict | None) -> None:
    """Propagate a CURRICULUM_MAPPING decision to its `ChunkMapping` and the
    exercise row."""

    if item.item_type is not ReviewItemType.CURRICULUM_MAPPING:
        return
    mapping = session.get(ChunkMapping, item.ref_id)
    if mapping is None:
        return

    if decision is ReviewDecisionType.APPROVE:
        mapping.mapping_status = MappingStatus.APPROVED
        apply_mapping_to_exercise(session, mapping, topic_id=mapping.topic_id)
    elif decision is ReviewDecisionType.REJECT:
        mapping.mapping_status = MappingStatus.REJECTED
        apply_mapping_to_exercise(session, mapping, topic_id=None)
    elif decision is ReviewDecisionType.EDIT and edit:
        if "topic_id" in edit:
            mapping.topic_id = edit["topic_id"]
            item.topic_id = edit["topic_id"]
        if "difficulty" in edit:
            mapping.difficulty = edit["difficulty"]
        if "content_type" in edit:
            mapping.content_type = edit["content_type"]
        mapping.mapping_status = MappingStatus.REVIEW_REQUIRED


def record_decision(
    session: Session,
    item_id: int,
    *,
    reviewer: str,
    decision: ReviewDecisionType,
    reason_code: ReviewReasonCode | None = None,
    note: str | None = None,
    edit: dict | None = None,
) -> ReviewDecision:
    item = session.get(ReviewItem, item_id)
    if item is None:
        raise ReviewError(f"review_item {item_id} not found")
    if item.status is not ReviewStatus.OPEN and decision is not ReviewDecisionType.EDIT:
        raise ReviewError(f"review_item {item_id} is already {item.status.value}")
    if decision is ReviewDecisionType.REJECT and reason_code is None:
        raise ReviewError("a rejection needs a reason_code")

    prior_status = item.status.value

    dec = ReviewDecision(
        review_item_id=item.id,
        reviewer=reviewer,
        decision=decision,
        reason_code=reason_code,
        prior_status=prior_status,
        note=note,
    )
    session.add(dec)

    _resolve_mapping(session, item, decision, edit)

    if decision is ReviewDecisionType.APPROVE:
        item.status = ReviewStatus.APPROVED
        item.resolved_at = _now()
    elif decision is ReviewDecisionType.REJECT:
        item.status = ReviewStatus.REJECTED
        item.resolved_at = _now()
    # EDIT leaves the item OPEN for a follow-up approve

    session.flush()
    return dec


def batch_approve(
    session: Session, item_ids: list[int], *, reviewer: str, note: str = "batch"
) -> int:
    """Approve several items at once. They must share a topic and a source and
    all be confident enough (SPEC §9); otherwise nothing is written."""

    if not item_ids:
        return 0
    items = session.scalars(
        select(ReviewItem).where(ReviewItem.id.in_(item_ids))
    ).all()
    found = {i.id for i in items}
    missing = set(item_ids) - found
    if missing:
        raise ReviewError(f"unknown review_item ids: {sorted(missing)}")

    open_items = [i for i in items if i.status is ReviewStatus.OPEN]
    if not open_items:
        return 0

    keys = {(i.topic_id, i.source_document_id) for i in open_items}
    if len(keys) != 1:
        raise ReviewError("batch approve requires one shared (topic, source_document)")
    if any((i.confidence or 0.0) < BATCH_MIN_CONFIDENCE for i in open_items):
        raise ReviewError(f"every item must have confidence >= {BATCH_MIN_CONFIDENCE}")

    for i in open_items:
        record_decision(
            session, i.id, reviewer=reviewer, decision=ReviewDecisionType.APPROVE, note=note
        )
    return len(open_items)
