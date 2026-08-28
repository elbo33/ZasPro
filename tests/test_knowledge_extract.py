"""Knowledge extraction: business rules + misconception source handling (M4)."""

from __future__ import annotations

import pytest

from tests.fixtures.mapping_world import build_world
from zaspro.db.models import (
    ChunkMapping, ContentType, ExerciseTopic, KnowledgeFlag,
    MappingStatus, Misconception, MisconceptionSource, ReviewItem, ReviewItemType,
    ReviewStatus, TopicRole,
)
from zaspro.db.models import KnowledgeExtraction as KnowledgeExtractionRow
from zaspro.knowledge import export as kexport
from zaspro.knowledge.agent import (
    ConceptOut, KnowledgeExtraction, MisconceptionOut, MethodOut,
)
from zaspro.knowledge.extract import KnowledgeFrozen, extract_topic


@pytest.fixture(autouse=True)
def _kroot(tmp_path, monkeypatch):
    """Point the export/freeze root at a tmp dir so tests never touch (or are
    tripped by) a real knowledge/topics/ file."""
    monkeypatch.setattr(kexport, "KNOWLEDGE_ROOT", tmp_path / "knowledge")


def _topic_with_two_exercises(db):
    """VIII.2 gets exercises 1 and 4 as PRIMARY (via exercise_topics)."""
    w = build_world(db)
    for num in ("1", "4"):
        ex = db.query(__import__("zaspro.db.models", fromlist=["Exercise"]).Exercise).filter_by(
            source_document_id=w.document_id, exercise_number=num
        ).one()
        db.add(ExerciseTopic(
            exercise_id=ex.id, topic_id=w.topic_ids["VIII.2"],
            role=TopicRole.PRIMARY, confidence=0.9,
        ))
    db.flush()
    return w


def _agent(extraction: KnowledgeExtraction):
    class A:
        name, model, prompt_version = "fake", None, "x"
        last_usage = None

        def extract(self, request):
            self._req = request
            return extraction
    return A()


def test_only_cited_exercises_that_exist_are_kept(db):
    w = _topic_with_two_exercises(db)
    ext = KnowledgeExtraction(concepts=[
        ConceptOut(name="c", description="d", from_exercises=["1", "99"], evidence="e"),
    ])
    res = extract_topic(db, w.topic_ids["VIII.2"], _agent(ext))
    assert res.concepts == 1
    from zaspro.db.models import Concept
    c = db.query(Concept).one()
    # chunk for "99" doesn't exist -> dropped; "1" -> its chunk id
    assert len(c.source_chunk_ids) == 1


def test_from_exercises_tolerates_zadanie_phrasing(db):
    w = _topic_with_two_exercises(db)
    ext = KnowledgeExtraction(concepts=[
        ConceptOut(name="c", description="d",
                   from_exercises=["Zadanie 1", "Zad 4 dystraktory B and D"],
                   evidence="e"),
    ])
    extract_topic(db, w.topic_ids["VIII.2"], _agent(ext))
    from zaspro.db.models import Concept
    assert len(db.query(Concept).one().source_chunk_ids) == 2


def test_citation_recovered_from_evidence_prose_when_field_empty(db):
    w = _topic_with_two_exercises(db)
    ext = KnowledgeExtraction(concepts=[
        ConceptOut(name="c", description="d", from_exercises=[],
                   evidence="widać to w Zadaniu 4, gdzie liczą pole"),
    ])
    extract_topic(db, w.topic_ids["VIII.2"], _agent(ext))
    from zaspro.db.models import Concept
    assert len(db.query(Concept).one().source_chunk_ids) == 1


def test_agent_inference_without_a_cited_exercise_becomes_unsourced_and_flags(db):
    w = _topic_with_two_exercises(db)
    ext = KnowledgeExtraction(misconceptions=[
        MisconceptionOut(
            name="students forget the domain", incorrect_reasoning="x",
            correct_reasoning="y", source_kind=MisconceptionSource.AGENT_INFERENCE,
            from_exercises=[], evidence="prior about rational equations",
        ),
    ])
    res = extract_topic(db, w.topic_ids["VIII.2"], _agent(ext))
    assert res.unsourced_misconceptions == 1
    mc = db.query(Misconception).one()
    assert mc.source_kind is MisconceptionSource.UNSOURCED
    assert db.query(KnowledgeFlag).filter_by(item_kind="misconception").count() == 1


def test_agent_inference_with_a_citation_is_kept_but_still_flagged(db):
    """ADR 0011: an inferred misconception is not dropped — it's emitted,
    labelled AGENT_INFERENCE, and flagged for the reviewer."""
    w = _topic_with_two_exercises(db)
    ext = KnowledgeExtraction(misconceptions=[
        MisconceptionOut(
            name="confuses area with perimeter", incorrect_reasoning="x",
            correct_reasoning="y", source_kind=MisconceptionSource.AGENT_INFERENCE,
            from_exercises=["1"], evidence="Zad 1 asks for area; a common slip is 2(a+b)",
        ),
    ])
    res = extract_topic(db, w.topic_ids["VIII.2"], _agent(ext))
    assert res.unsourced_misconceptions == 0
    assert res.flagged_misconceptions == 1
    mc = db.query(Misconception).one()
    assert mc.source_kind is MisconceptionSource.AGENT_INFERENCE
    assert len(mc.source_chunk_ids) == 1                       # citation kept
    assert db.query(KnowledgeFlag).filter_by(item_kind="misconception").count() == 1


def test_extraction_creates_one_review_card_and_an_extraction_row(db):
    w = _topic_with_two_exercises(db)
    ext = KnowledgeExtraction(concepts=[
        ConceptOut(name="c", description="d", from_exercises=["1"], evidence="e"),
    ])
    res = extract_topic(db, w.topic_ids["VIII.2"], _agent(ext))

    ri = db.query(ReviewItem).filter_by(item_type=ReviewItemType.KNOWLEDGE_SPEC).one()
    assert ri.ref_table == "topics" and ri.ref_id == w.topic_ids["VIII.2"]
    assert ri.status is ReviewStatus.OPEN
    assert res.review_item_id == ri.id

    ke = db.query(KnowledgeExtractionRow).filter_by(topic_id=w.topic_ids["VIII.2"]).one()
    assert ke.agent_name == "fake" and ke.exercises == 2
    assert ke.review_item_id == ri.id and ke.exported_at is None

    # re-extracting reuses (and reopens) the one card
    extract_topic(db, w.topic_ids["VIII.2"], _agent(KnowledgeExtraction()))
    assert db.query(ReviewItem).filter_by(
        item_type=ReviewItemType.KNOWLEDGE_SPEC
    ).count() == 1


def test_a_frozen_topic_refuses_re_extraction_without_force(db, tmp_path):
    w = _topic_with_two_exercises(db)
    a = _agent(KnowledgeExtraction())
    extract_topic(db, w.topic_ids["VIII.2"], a)

    # simulate the committed export file
    (kexport.KNOWLEDGE_ROOT).mkdir(parents=True, exist_ok=True)
    kexport.export_path("VIII.2").write_text("requirement_code: VIII.2\n")

    with pytest.raises(KnowledgeFrozen):
        extract_topic(db, w.topic_ids["VIII.2"], a)
    # force overrides
    extract_topic(db, w.topic_ids["VIII.2"], a, force=True)


def test_distractor_inference_with_a_cited_task_is_a_real_source(db):
    w = _topic_with_two_exercises(db)
    ext = KnowledgeExtraction(misconceptions=[
        MisconceptionOut(
            name="adds instead of compounding", incorrect_reasoning="x",
            correct_reasoning="y",
            source_kind=MisconceptionSource.DISTRACTOR_INFERENCE,
            from_exercises=["1"], distractor="C: 20000 · 1,06",
            evidence="Zad 1 dystraktor C is 20000 · 1,06",
        ),
    ])
    res = extract_topic(db, w.topic_ids["VIII.2"], _agent(ext))
    assert res.unsourced_misconceptions == 0
    assert res.misconception_sources == {"DISTRACTOR_INFERENCE": 1}
    mc = db.query(Misconception).one()
    assert mc.source_kind is MisconceptionSource.DISTRACTOR_INFERENCE
    assert mc.distractor == "C: 20000 · 1,06"
    assert len(mc.source_chunk_ids) == 1


def test_distractor_inference_without_a_cited_task_becomes_unsourced(db):
    w = _topic_with_two_exercises(db)
    ext = KnowledgeExtraction(misconceptions=[
        MisconceptionOut(
            name="floating claim", incorrect_reasoning="x", correct_reasoning="y",
            source_kind=MisconceptionSource.DISTRACTOR_INFERENCE,
            from_exercises=[], distractor="B", evidence="no task named here",
        ),
    ])
    res = extract_topic(db, w.topic_ids["VIII.2"], _agent(ext))
    assert res.unsourced_misconceptions == 1
    assert db.query(Misconception).one().source_kind is MisconceptionSource.UNSOURCED


def test_marking_scheme_misconception_is_kept_as_is(db):
    w = _topic_with_two_exercises(db)
    ext = KnowledgeExtraction(misconceptions=[
        MisconceptionOut(
            name="sign error on the discriminant", incorrect_reasoning="x",
            correct_reasoning="y", source_kind=MisconceptionSource.MARKING_SCHEME,
            from_exercises=["1"], evidence="0 pkt jeśli błąd znaku",
        ),
    ])
    res = extract_topic(db, w.topic_ids["VIII.2"], _agent(ext))
    assert res.unsourced_misconceptions == 0
    assert res.misconception_sources == {"MARKING_SCHEME": 1}


def test_reextract_replaces_prior_items(db):
    w = _topic_with_two_exercises(db)
    a = _agent(KnowledgeExtraction(methods=[
        MethodOut(name="m1", when_to_use="w", from_exercises=["1"], evidence="e"),
        MethodOut(name="m2", when_to_use="w", from_exercises=["4"], evidence="e"),
    ]))
    extract_topic(db, w.topic_ids["VIII.2"], a)
    extract_topic(db, w.topic_ids["VIII.2"], _agent(KnowledgeExtraction()))
    from zaspro.db.models import Method
    assert db.query(Method).count() == 0  # replaced with nothing


def test_pick_calibration_topics_is_a_deliberate_spread(db):
    w = build_world(db)
    # VIII.1 primary x1 + secondary via two exercises -> touch; VIII.3 nothing
    from zaspro.db.models import Exercise
    exs = db.query(Exercise).filter_by(source_document_id=w.document_id).all()
    db.add(ExerciseTopic(exercise_id=exs[0].id, topic_id=w.topic_ids["VIII.1"],
                         role=TopicRole.PRIMARY, confidence=0.9))
    db.add(ExerciseTopic(exercise_id=exs[1].id, topic_id=w.topic_ids["VIII.1"],
                         role=TopicRole.SECONDARY, confidence=0.4))
    db.flush()

    from zaspro.knowledge.run import pick_calibration_topics
    picks = pick_calibration_topics(db, 5)
    codes = [c for c, _, _ in picks]
    assert len(codes) == len(set(codes))  # no dup across buckets


def test_all_podstawowy_lists_only_coded_podstawowy_topics(db):
    from zaspro.knowledge.run import _all_podstawowy

    w = build_world(db)
    codes = [c for c, _, _ in _all_podstawowy(db)]
    assert {"VIII.1", "VIII.2", "VIII.3"} <= set(codes)
    assert "VIII.R1" not in codes            # rozszerzony excluded
    assert codes == sorted(codes)            # deterministic order
