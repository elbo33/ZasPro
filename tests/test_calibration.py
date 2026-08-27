"""The agreement-vs-confidence curve (ADR 0009, calibration instrumentation)."""

from __future__ import annotations

from tests.fixtures.mapping_world import build_world
from zaspro.db.models import ChunkMapping, MappingStatus, ReviewDecisionType, ReviewReasonCode
from zaspro.mapping.handler import map_chunk
from zaspro.review import Band, agreement_curve, next_item, record_decision, recommend_threshold
from zaspro.mapping import StubMappingAgent


def _band(lo, hi, agree, disagree):
    return Band(lo=lo, hi=hi, n=agree + disagree, agree=agree, disagree=disagree)


def test_recommender_from_the_2405_calibration():
    # the real calibration bands: 1@0%, 9@100%, 4@75%, 9@100%, 14@100%
    bands = [
        _band(0.0, 0.5, 0, 1),
        _band(0.5, 0.7, 9, 0),
        _band(0.7, 0.8, 3, 1),
        _band(0.8, 0.9, 9, 0),
        _band(0.9, 1.0, 14, 0),
    ]
    t, reason = recommend_threshold(bands)
    assert t == 0.8 and reason is None


def test_thin_below_target_band_blocks_and_is_not_skipped():
    # the bug: n=1 band at 0% used to be skipped, giving a 0.00 recommendation
    bands = [
        _band(0.0, 0.5, 0, 1),   # thin, 0%  -> must block 0.0
        _band(0.5, 0.7, 0, 0),
        _band(0.7, 0.8, 0, 0),
        _band(0.8, 0.9, 8, 0),
        _band(0.9, 1.0, 8, 0),
    ]
    t, reason = recommend_threshold(bands)
    assert t == 0.8  # 0.0 is blocked by the thin 0% band; 0.8 is the first clean cutoff


def test_thin_cutoff_band_reports_insufficient_data_not_a_number():
    bands = [
        _band(0.0, 0.5, 0, 0),
        _band(0.5, 0.7, 0, 0),
        _band(0.7, 0.8, 0, 0),
        _band(0.8, 0.9, 2, 0),   # 100% but only n=2 -> cutoff too thin
        _band(0.9, 1.0, 3, 0),   # also thin
    ]
    t, reason = recommend_threshold(bands)
    assert t is None
    assert "insufficient data" in reason


def test_no_band_clears_target():
    bands = [_band(lo, hi, 1, 1) for lo, hi in
             [(0.0, 0.5), (0.5, 0.7), (0.7, 0.8), (0.8, 0.9), (0.9, 1.0)]]
    t, reason = recommend_threshold(bands)
    assert t is None and "clears" in reason


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
