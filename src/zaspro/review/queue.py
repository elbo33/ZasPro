"""The single review queue (SPEC §9).

One queue, typed items, sorted so the doubtful things surface first
(`risk` desc). Deterministically extracted content never lands here on its own —
only an uncertain downstream *mapping* does (SPEC §9, §10). Every decision is
appended immutably with reviewer, timestamp and prior status; a rejection
carries a reason code (the DB enforces it too).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from zaspro.db.models import (
    ChunkMapping,
    Concept,
    Example,
    Formula,
    KnowledgeExtraction,
    KnowledgeFlag,
    LearningObjective,
    MappingStatus,
    Method,
    Misconception,
    ReviewDecision,
    ReviewDecisionType,
    ReviewItem,
    ReviewItemType,
    ReviewReasonCode,
    ReviewStatus,
    SourceChunk,
    VerificationStatus,
)
from zaspro.mapping.handler import apply_mapping_to_exercise

# knowledge item kind -> model, for KNOWLEDGE_SPEC card resolution
_KNOWLEDGE_MODELS = {
    "concept": Concept,
    "formula": Formula,
    "method": Method,
    "example": Example,
    "objective": LearningObjective,
    "misconception": Misconception,
}

# batch approval is only offered above this (SPEC §9: "sharing high confidence")
BATCH_MIN_CONFIDENCE = 0.6

_SUBTASK_HEADING = re.compile(r"Zadanie\s+\d+\.\d+")


def flag_stem_defect_reviews(session: Session, *, current_prompt_version: str) -> int:
    """Mark resolved CURRICULUM_MAPPING items where a **subtask** was mapped
    without its parent's stem (the v1 pipeline bug — the agent got the bare
    subtask body). Those decisions are not evidence about the agent and are
    excluded from the calibration curve until the chunk is remapped.

    Idempotent: an item already flagged, or one whose mapping is at the current
    (fixed) prompt version, is left alone. Returns the number newly flagged.
    """

    items = session.scalars(
        select(ReviewItem).where(
            ReviewItem.item_type == ReviewItemType.CURRICULUM_MAPPING,
            ReviewItem.status != ReviewStatus.OPEN,
            ReviewItem.input_defect.is_(False),
        )
    ).all()
    flagged = 0
    for item in items:
        mapping = session.get(ChunkMapping, item.ref_id)
        if mapping is None or mapping.prompt_version == current_prompt_version:
            continue
        chunk = session.get(SourceChunk, mapping.source_chunk_id)
        if chunk is None or not chunk.heading or not _SUBTASK_HEADING.match(chunk.heading):
            continue
        item.input_defect = True
        flagged += 1
    session.flush()
    return flagged


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
        select(ChunkMapping.mapping_status, func.count())
        .where(ChunkMapping.is_primary.is_(True))
        .group_by(ChunkMapping.mapping_status)
    ):
        mappings_by_status[status.value] = n

    unmapped_chunks = session.scalar(
        select(func.count())
        .select_from(SourceChunk)
        .outerjoin(
            ChunkMapping,
            (ChunkMapping.source_chunk_id == SourceChunk.id)
            & ChunkMapping.is_primary.is_(True),
        )
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


def _promote_secondary(session: Session, item: ReviewItem, edit: dict | None) -> None:
    """Swap a secondary `ChunkMapping` into the primary slot (the agent's
    primary was the wrong primary). One keystroke on the review card."""

    old_primary = session.get(ChunkMapping, item.ref_id)
    if old_primary is None:
        raise ReviewError(f"review_item {item.id}: primary mapping is gone")

    target_id = (edit or {}).get("promote_mapping_id")
    if target_id is None:
        # default: the highest-confidence secondary
        secs = session.scalars(
            select(ChunkMapping)
            .where(
                ChunkMapping.source_chunk_id == old_primary.source_chunk_id,
                ChunkMapping.is_primary.is_(False),
            )
            .order_by(ChunkMapping.confidence.desc(), ChunkMapping.id)
        ).all()
        if not secs:
            raise ReviewError("no secondary mapping to promote")
        new_primary = secs[0]
    else:
        new_primary = session.get(ChunkMapping, target_id)
        if (
            new_primary is None
            or new_primary.source_chunk_id != old_primary.source_chunk_id
            or new_primary.is_primary
        ):
            raise ReviewError(
                f"mapping {target_id} is not a secondary of this chunk"
            )

    # two statements, flush between: the partial unique index forbids two
    # is_primary rows for a chunk even transiently
    old_primary.is_primary = False
    old_primary.mapping_status = MappingStatus.AI_SUGGESTED  # still a plausible secondary
    session.flush()
    new_primary.is_primary = True
    new_primary.mapping_status = MappingStatus.APPROVED
    session.flush()

    apply_mapping_to_exercise(session, new_primary, topic_id=new_primary.topic_id)

    # the review item now tracks the new primary
    item.ref_id = new_primary.id
    item.topic_id = new_primary.topic_id
    item.confidence = new_primary.confidence


def _knowledge_items(session: Session, topic_id: int) -> list:
    items: list = []
    for model in _KNOWLEDGE_MODELS.values():
        items += list(session.scalars(select(model).where(model.topic_id == topic_id)))
    return items


def _resolve_knowledge(session: Session, item: ReviewItem, decision: ReviewDecisionType,
                       edit: dict | None) -> None:
    """Resolve a KNOWLEDGE_SPEC card (one per topic, ADR 0011).

    EDIT   — `edit={"reject_items": [["misconception", 12], ...]}` (and the
             inverse `"unreject_items"`) sets individual item statuses and
             leaves the card OPEN for a follow-up APPROVE.
    APPROVE — every item not individually REJECTED becomes APPROVED.
    REJECT  — every item becomes REJECTED (the whole spec is thrown out).
    """
    topic_id = item.ref_id
    by_key = {
        (kind, obj.id): obj
        for kind, model in _KNOWLEDGE_MODELS.items()
        for obj in session.scalars(select(model).where(model.topic_id == topic_id))
    }

    if decision is ReviewDecisionType.EDIT:
        for kind, oid in (edit or {}).get("reject_items", []):
            obj = by_key.get((kind, oid))
            if obj is not None:
                obj.verification_status = VerificationStatus.REJECTED
        for kind, oid in (edit or {}).get("unreject_items", []):
            obj = by_key.get((kind, oid))
            if obj is not None:
                obj.verification_status = VerificationStatus.AI_GENERATED
        session.flush()
        return

    if decision is ReviewDecisionType.APPROVE:
        for obj in by_key.values():
            if obj.verification_status is not VerificationStatus.REJECTED:
                obj.verification_status = VerificationStatus.APPROVED
    elif decision is ReviewDecisionType.REJECT:
        for obj in by_key.values():
            obj.verification_status = VerificationStatus.REJECTED
        session.query(KnowledgeFlag).filter_by(topic_id=topic_id).update(
            {"resolved": True}
        )

    ke = session.scalars(
        select(KnowledgeExtraction).where(KnowledgeExtraction.topic_id == topic_id)
    ).one_or_none()
    if ke is not None and decision is ReviewDecisionType.APPROVE:
        ke.approved_at = _now()
    session.flush()


def _resolve_mapping(session: Session, item: ReviewItem, decision: ReviewDecisionType,
                     edit: dict | None) -> None:
    """Propagate a CURRICULUM_MAPPING decision to its `ChunkMapping` and the
    exercise row."""

    if item.item_type is ReviewItemType.KNOWLEDGE_SPEC:
        _resolve_knowledge(session, item, decision, edit)
        return

    if item.item_type is not ReviewItemType.CURRICULUM_MAPPING:
        return

    if decision is ReviewDecisionType.PROMOTE:
        _promote_secondary(session, item, edit)
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

    # freeze the mapping's confidence onto the decision (calibration data)
    mapping_confidence = None
    if item.item_type is ReviewItemType.CURRICULUM_MAPPING:
        m = session.get(ChunkMapping, item.ref_id)
        mapping_confidence = m.confidence if m is not None else None

    dec = ReviewDecision(
        review_item_id=item.id,
        reviewer=reviewer,
        decision=decision,
        reason_code=reason_code,
        prior_status=prior_status,
        note=note,
        mapping_confidence=mapping_confidence,
    )
    session.add(dec)

    _resolve_mapping(session, item, decision, edit)

    if (
        item.item_type is ReviewItemType.KNOWLEDGE_SPEC
        and decision is ReviewDecisionType.APPROVE
    ):
        ke = session.scalars(
            select(KnowledgeExtraction).where(
                KnowledgeExtraction.topic_id == item.ref_id
            )
        ).one_or_none()
        if ke is not None and not ke.approved_by:
            ke.approved_by = reviewer

    if decision in (ReviewDecisionType.APPROVE, ReviewDecisionType.PROMOTE):
        # PROMOTE = "the agent's secondary was the right primary, use it" — a
        # resolution, one keystroke, not a two-step edit-then-approve
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
