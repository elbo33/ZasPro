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


def test_input_defect_items_are_excluded_from_the_curve(db):
    from zaspro.db.models import ReviewItem

    w = build_world(db)
    _queue_all(db, w)
    # resolve all four
    for _ in range(4):
        it = next_item(db)
        record_decision(db, it.id, reviewer="e", decision=ReviewDecisionType.APPROVE)

    cal = agreement_curve(db)
    assert cal.resolved == 4 and cal.excluded_defective == 0

    # mark two as defective input
    marked = 0
    for it in db.query(ReviewItem).all():
        if marked < 2:
            it.input_defect = True
            marked += 1
    db.flush()

    cal = agreement_curve(db)
    assert cal.resolved == 2
    assert cal.excluded_defective == 2
    assert any("input_defect" in n for n in cal.notes)


def test_flag_stem_defect_reviews_targets_stale_subtasks(db):
    from zaspro.db.models import (
        ChunkMapping, ContentType as CT, ExtractionMethod as EM, ReviewItem, SourceChunk as SC,
    )
    from zaspro.mapping.agent import MappingResult
    from zaspro.mapping.handler import map_chunk
    from zaspro.review import flag_stem_defect_reviews

    w = build_world(db)
    # a subtask chunk mapped at an OLD prompt version -> should be flagged
    sub = SC(source_document_id=w.document_id, heading="Zadanie 9.1.", section="9",
             content_type=CT.EXERCISE, text="Podaj dziesiąty wyraz.", latex="x",
             order_index=9, extraction_method=EM.pandoc_omml, confidence=None)
    db.add(sub)
    db.flush()

    class OldAgent:
        name, model, prompt_version = "old", None, "m3-map-v1"

        def map(self, request):
            return MappingResult(topic_id=None, content_type=CT.EXERCISE,
                                 confidence=0.3, rationale="bare subtask")

    m = map_chunk(db, sub.id, OldAgent())          # subtask, old version -> flag
    m1 = map_chunk(db, w.chunk_ids["3"], OldAgent())  # top-level, old version -> no flag
    for it in db.query(ReviewItem).all():
        record_decision(db, it.id, reviewer="e", decision=ReviewDecisionType.APPROVE)

    n = flag_stem_defect_reviews(db, current_prompt_version="m3-map-v2")
    assert n == 1
    flagged = [it for it in db.query(ReviewItem).all() if it.input_defect]
    assert len(flagged) == 1 and flagged[0].ref_id == m.id
    # idempotent
    assert flag_stem_defect_reviews(db, current_prompt_version="m3-map-v2") == 0
