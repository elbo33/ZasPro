"""The agreement-vs-confidence curve (ADR 0009, calibration instrumentation)."""

from __future__ import annotations

from tests.fixtures.mapping_world import build_world
from zaspro.db.models import ChunkMapping, MappingStatus, ReviewDecisionType, ReviewReasonCode
from zaspro.mapping.handler import map_chunk
from zaspro.review import agreement_curve, next_item, record_decision
from zaspro.mapping import StubMappingAgent


def _queue_all(db, w):
    # threshold 1.01 -> every mapping is REVIEW_REQUIRED and lands in the queue
    for num in ("1", "2", "3", "4"):
        map_chunk(db, w.chunk_ids[num], StubMappingAgent(), threshold=1.01)


def test_decision_freezes_mapping_confidence(db):
    w = build_world(db)
    _queue_all(db, w)
    item = next_item(db)
    conf = db.query(ChunkMapping).filter_by(id=item.ref_id).one().confidence
    dec = record_decision(
        db, item.id, reviewer="e", decision=ReviewDecisionType.APPROVE
    )
    assert dec.mapping_confidence == conf


def test_curve_buckets_by_confidence_and_recommends(db):
    w = build_world(db)
    _queue_all(db, w)

    # approve everything with confidence >= 0.9, reject the rest — a clean split
    for _ in range(10):
        item = next_item(db)
        if item is None:
            break
        m = db.query(ChunkMapping).filter_by(id=item.ref_id).one()
        if (m.confidence or 0) >= 0.9:
            record_decision(db, item.id, reviewer="e", decision=ReviewDecisionType.APPROVE)
        else:
            record_decision(
                db, item.id, reviewer="e",
                decision=ReviewDecisionType.REJECT, reason_code=ReviewReasonCode.WRONG_TOPIC,
            )

    cal = agreement_curve(db)
    assert cal.resolved == 4
    assert cal.pending == 0
    # the [0.9, 1.0] band is all agreement; a low band is all disagreement
    top = next(b for b in cal.bands if b.lo == 0.9)
    assert top.n >= 1 and top.agreement == 1.0
    low = next(b for b in cal.bands if b.lo == 0.0)
    assert low.disagree == low.n and low.n >= 1


def test_curve_is_empty_before_any_review(db):
    w = build_world(db)
    _queue_all(db, w)
    cal = agreement_curve(db)
    assert cal.resolved == 0
    assert cal.recommended_threshold is None
    assert any("calibration pass" in n for n in cal.notes)
