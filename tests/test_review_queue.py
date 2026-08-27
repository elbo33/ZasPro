"""Review queue backend (SPEC §9): ordering, decisions, propagation, batch."""

from __future__ import annotations

import pytest

from tests.fixtures.mapping_world import build_world
from zaspro.db.models import (
    Exercise,
    MappingStatus,
    ReviewDecisionType,
    ReviewReasonCode,
    ReviewStatus,
)
from zaspro.mapping import StubMappingAgent, map_document
from zaspro.mapping.handler import map_chunk
from zaspro.review import (
    ReviewError,
    batch_approve,
    batch_groups,
    next_item,
    queue_stats,
    record_decision,
)


def _seed_two_review_items(db):
    """chunk 2 (weak overlap) and chunk 3 (no match) -> two OPEN items of
    different risk."""
    w = build_world(db)
    m2 = map_chunk(db, w.chunk_ids["2"], StubMappingAgent())
    m3 = map_chunk(db, w.chunk_ids["3"], StubMappingAgent())
    return w, m2, m3


def test_next_item_returns_highest_risk_first(db):
    _seed_two_review_items(db)
    first = next_item(db)
    # chunk 3 has the lower confidence -> higher risk -> shown first
    assert first.risk == max(i.risk for i in db_all_open(db))
    second = next_item(db, exclude_ids={first.id})
    assert second.id != first.id
    assert first.risk >= second.risk


def db_all_open(db):
    from zaspro.db.models import ReviewItem

    return db.query(ReviewItem).filter_by(status=ReviewStatus.OPEN).all()


def test_approve_records_decision_and_propagates_topic(db):
    w = build_world(db)
    # force chunk 2 into review with a known topic guess by editing confidence
    m = map_chunk(db, w.chunk_ids["2"], StubMappingAgent())
    if m.mapping_status is not MappingStatus.REVIEW_REQUIRED:
        pytest.skip("stub mapped chunk 2 confidently; fixture assumption changed")
    m.topic_id = w.topic_ids["VIII.1"]
    db.flush()
    from zaspro.db.models import ReviewItem

    item = db.query(ReviewItem).filter_by(ref_id=m.id).one()
    item.topic_id = w.topic_ids["VIII.1"]
    db.flush()

    dec = record_decision(
        db, item.id, reviewer="elie", decision=ReviewDecisionType.APPROVE
    )
    assert dec.prior_status == "OPEN"
    db.refresh(item)
    db.refresh(m)
    assert item.status is ReviewStatus.APPROVED
    assert item.resolved_at is not None
    assert m.mapping_status is MappingStatus.APPROVED
    ex = db.query(Exercise).filter_by(
        source_document_id=w.document_id, exercise_number="2"
    ).one()
    assert ex.topic_id == w.topic_ids["VIII.1"]


def test_reject_requires_a_reason_code(db):
    _seed_two_review_items(db)
    item = next_item(db)
    with pytest.raises(ReviewError, match="reason_code"):
        record_decision(db, item.id, reviewer="elie", decision=ReviewDecisionType.REJECT)

    dec = record_decision(
        db,
        item.id,
        reviewer="elie",
        decision=ReviewDecisionType.REJECT,
        reason_code=ReviewReasonCode.NOT_CURRICULUM,
    )
    db.refresh(item)
    assert item.status is ReviewStatus.REJECTED
    assert dec.reason_code is ReviewReasonCode.NOT_CURRICULUM


def test_cannot_decide_a_resolved_item_twice(db):
    _seed_two_review_items(db)
    item = next_item(db)
    record_decision(db, item.id, reviewer="e", decision=ReviewDecisionType.APPROVE)
    with pytest.raises(ReviewError, match="already"):
        record_decision(db, item.id, reviewer="e", decision=ReviewDecisionType.APPROVE)


def test_edit_changes_the_mapping_and_leaves_the_item_open(db):
    w = _seed_two_review_items(db)[0]
    item = next_item(db)
    record_decision(
        db,
        item.id,
        reviewer="elie",
        decision=ReviewDecisionType.EDIT,
        edit={"topic_id": w.topic_ids["VIII.3"], "difficulty": 3},
    )
    db.refresh(item)
    assert item.status is ReviewStatus.OPEN
    from zaspro.db.models import ChunkMapping

    m = db.get(ChunkMapping, item.ref_id)
    assert m.topic_id == w.topic_ids["VIII.3"]
    assert m.difficulty == 3


def test_queue_stats_shape(db):
    w = build_world(db)
    map_document(db, w.document_id, StubMappingAgent(), inline=True)
    st = queue_stats(db)
    assert st.open_total == st.by_type["CURRICULUM_MAPPING"]
    assert sum(st.mappings_by_status.values()) == 4
    assert st.unmapped_chunks == 0  # every chunk now has a mapping row


def test_batch_approve_needs_shared_topic_and_source(db):
    w = build_world(db)
    # chunks 1 and 4 both cite VIII.2 and are confident -> not in queue.
    # Build a batch by forcing both into review with the same topic.
    from zaspro.db.models import ReviewItem, ReviewStatus as RS

    ids = []
    for num in ("1", "4"):
        m = map_chunk(db, w.chunk_ids[num], StubMappingAgent(), threshold=0.99)
        assert m.mapping_status is MappingStatus.REVIEW_REQUIRED
        it = db.query(ReviewItem).filter_by(ref_id=m.id).one()
        ids.append(it.id)

    groups = batch_groups(db)
    assert any(set(g.item_ids) == set(ids) for g in groups)

    n = batch_approve(db, ids, reviewer="elie")
    assert n == 2
    assert db.query(ReviewItem).filter_by(status=RS.OPEN).count() == 0


def test_batch_approve_rejects_mixed_groups(db):
    w = build_world(db)
    from zaspro.db.models import ReviewItem

    ids = []
    for num in ("1", "2"):  # different topics
        m = map_chunk(db, w.chunk_ids[num], StubMappingAgent(), threshold=0.99)
        it = db.query(ReviewItem).filter_by(ref_id=m.id).one()
        it.confidence = 0.9  # lift above BATCH_MIN_CONFIDENCE
        ids.append(it.id)
    db.flush()
    with pytest.raises(ReviewError, match="shared"):
        batch_approve(db, ids, reviewer="elie")
