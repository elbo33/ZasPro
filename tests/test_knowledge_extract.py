"""Knowledge extraction: citation recovery + provenance labelling (M4)."""

from __future__ import annotations

import pytest

from tests.fixtures.mapping_world import build_world
from zaspro.db.models import (
    Concept, Exercise, ExerciseTopic, KnowledgeProvenance, Method, Misconception,
    ReviewItem, ReviewItemType, ReviewStatus, TopicRole,
)
from zaspro.db.models import KnowledgeExtraction as KnowledgeExtractionRow
from zaspro.knowledge import export as kexport
from zaspro.knowledge.agent import (
    ConceptOut, KnowledgeExtraction, MethodOut, MisconceptionOut,
)
from zaspro.knowledge.extract import KnowledgeFrozen, extract_topic

_EXAM = KnowledgeProvenance.EXAM_TASK
_OWN = KnowledgeProvenance.AGENT_KNOWLEDGE
_DIST = KnowledgeProvenance.DISTRACTOR
_MS = KnowledgeProvenance.MARKING_SCHEME


@pytest.fixture(autouse=True)
def _kroot(tmp_path, monkeypatch):
    monkeypatch.setattr(kexport, "KNOWLEDGE_ROOT", tmp_path / "knowledge")


def _topic_with_two_exercises(db):
    """VIII.2 gets exercises 1 and 4 as PRIMARY (via exercise_topics)."""
    w = build_world(db)
    for num in ("1", "4"):
        ex = db.query(Exercise).filter_by(
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
        ConceptOut(name="c", description="d", provenance=_EXAM,
                   from_exercises=["1", "99"], evidence="e"),
    ])
    res = extract_topic(db, w.topic_ids["VIII.2"], _agent(ext))
    assert res.concepts == 1
    c = db.query(Concept).one()
    assert len(c.source_chunk_ids) == 1          # "99" dropped, "1" kept
    assert c.provenance is _EXAM


def test_from_exercises_tolerates_zadanie_phrasing(db):
    w = _topic_with_two_exercises(db)
    ext = KnowledgeExtraction(concepts=[
        ConceptOut(name="c", description="d", provenance=_EXAM,
                   from_exercises=["Zadanie 1", "Zad 4 dystraktory B and D"], evidence="e"),
    ])
    extract_topic(db, w.topic_ids["VIII.2"], _agent(ext))
    assert len(db.query(Concept).one().source_chunk_ids) == 2


def test_citation_recovered_from_evidence_prose_upgrades_provenance(db):
    w = _topic_with_two_exercises(db)
    ext = KnowledgeExtraction(concepts=[
        ConceptOut(name="c", description="d", provenance=_OWN, from_exercises=[],
                   evidence="widać to w Zadaniu 4, gdzie liczą pole"),
    ])
    extract_topic(db, w.topic_ids["VIII.2"], _agent(ext))
    c = db.query(Concept).one()
    assert len(c.source_chunk_ids) == 1
    assert c.provenance is _EXAM                 # bare AGENT_KNOWLEDGE + a real citation -> EXAM_TASK


def test_agent_knowledge_item_with_no_exercise_is_kept_as_is(db):
    w = _topic_with_two_exercises(db)
    ext = KnowledgeExtraction(misconceptions=[
        MisconceptionOut(
            name="students forget the domain", incorrect_reasoning="x",
            correct_reasoning="y", provenance=_OWN,
            from_exercises=[], evidence="a common error on rational equations",
        ),
    ])
    res = extract_topic(db, w.topic_ids["VIII.2"], _agent(ext))
    mc = db.query(Misconception).one()
    assert mc.provenance is _OWN                 # not downgraded, not flagged, not dropped
    assert res.provenance_counts == {"AGENT_KNOWLEDGE": 1}
    from zaspro.db.models import KnowledgeFlag
    assert db.query(KnowledgeFlag).count() == 0  # no GAP flag


def test_distractor_misconception_keeps_its_label_and_option(db):
    w = _topic_with_two_exercises(db)
    ext = KnowledgeExtraction(misconceptions=[
        MisconceptionOut(
            name="adds instead of compounding", incorrect_reasoning="x",
            correct_reasoning="y", provenance=_DIST,
            from_exercises=["1"], distractor="C: 20000 · 1,06",
            evidence="Zad 1 dystraktor C is 20000 · 1,06",
        ),
    ])
    res = extract_topic(db, w.topic_ids["VIII.2"], _agent(ext))
    mc = db.query(Misconception).one()
    assert mc.provenance is _DIST
    assert mc.distractor == "C: 20000 · 1,06"
    assert len(mc.source_chunk_ids) == 1
    assert res.provenance_counts == {"DISTRACTOR": 1}


def test_marking_scheme_item_kept_as_is(db):
    w = _topic_with_two_exercises(db)
    ext = KnowledgeExtraction(misconceptions=[
        MisconceptionOut(
            name="sign error on the discriminant", incorrect_reasoning="x",
            correct_reasoning="y", provenance=_MS,
            from_exercises=["1"], evidence="0 pkt jeśli błąd znaku",
        ),
    ])
    res = extract_topic(db, w.topic_ids["VIII.2"], _agent(ext))
    assert db.query(Misconception).one().provenance is _MS
    assert res.provenance_counts == {"MARKING_SCHEME": 1}


def test_empty_exercise_list_still_produces_a_spec(db):
    """A topic with zero exercises is extracted from the requirement text; the
    request carries no exercises and every item is AGENT_KNOWLEDGE."""
    w = build_world(db)  # no exercise_topics rows for VIII.3
    captured = {}

    class A:
        name, model, prompt_version = "fake", None, "x"
        last_usage = None

        def extract(self, request):
            captured["n"] = len(request.exercises)
            return KnowledgeExtraction(concepts=[
                ConceptOut(name="from text", description="d", provenance=_OWN,
                           from_exercises=[], evidence="from the requirement text"),
            ])

    res = extract_topic(db, w.topic_ids["VIII.3"], A())
    assert captured["n"] == 0
    assert res.concepts == 1
    assert db.query(Concept).one().provenance is _OWN


def test_extraction_creates_one_review_card_and_an_extraction_row(db):
    w = _topic_with_two_exercises(db)
    ext = KnowledgeExtraction(concepts=[
        ConceptOut(name="c", description="d", provenance=_EXAM,
                   from_exercises=["1"], evidence="e"),
    ])
    res = extract_topic(db, w.topic_ids["VIII.2"], _agent(ext))

    ri = db.query(ReviewItem).filter_by(item_type=ReviewItemType.KNOWLEDGE_SPEC).one()
    assert ri.ref_table == "topics" and ri.ref_id == w.topic_ids["VIII.2"]
    assert ri.status is ReviewStatus.OPEN
    assert res.review_item_id == ri.id

    ke = db.query(KnowledgeExtractionRow).filter_by(topic_id=w.topic_ids["VIII.2"]).one()
    assert ke.agent_name == "fake" and ke.exercises == 2

    extract_topic(db, w.topic_ids["VIII.2"], _agent(KnowledgeExtraction()))
    assert db.query(ReviewItem).filter_by(
        item_type=ReviewItemType.KNOWLEDGE_SPEC
    ).count() == 1


def test_a_frozen_topic_refuses_re_extraction_without_force(db):
    w = _topic_with_two_exercises(db)
    a = _agent(KnowledgeExtraction())
    extract_topic(db, w.topic_ids["VIII.2"], a)

    kexport.KNOWLEDGE_ROOT.mkdir(parents=True, exist_ok=True)
    kexport.export_path("VIII.2").write_text("requirement_code: VIII.2\n")

    with pytest.raises(KnowledgeFrozen):
        extract_topic(db, w.topic_ids["VIII.2"], a)
    extract_topic(db, w.topic_ids["VIII.2"], a, force=True)


def test_reextract_replaces_prior_items(db):
    w = _topic_with_two_exercises(db)
    a = _agent(KnowledgeExtraction(methods=[
        MethodOut(name="m1", when_to_use="w", provenance=_EXAM,
                  from_exercises=["1"], evidence="e"),
        MethodOut(name="m2", when_to_use="w", provenance=_EXAM,
                  from_exercises=["4"], evidence="e"),
    ]))
    extract_topic(db, w.topic_ids["VIII.2"], a)
    extract_topic(db, w.topic_ids["VIII.2"], _agent(KnowledgeExtraction()))
    assert db.query(Method).count() == 0


def test_pick_calibration_topics_is_a_deliberate_spread(db):
    w = build_world(db)
    exs = db.query(Exercise).filter_by(source_document_id=w.document_id).all()
    db.add(ExerciseTopic(exercise_id=exs[0].id, topic_id=w.topic_ids["VIII.1"],
                         role=TopicRole.PRIMARY, confidence=0.9))
    db.add(ExerciseTopic(exercise_id=exs[1].id, topic_id=w.topic_ids["VIII.1"],
                         role=TopicRole.SECONDARY, confidence=0.4))
    db.flush()

    from zaspro.knowledge.run import pick_calibration_topics
    picks = pick_calibration_topics(db, 5)
    codes = [c for c, _, _ in picks]
    assert len(codes) == len(set(codes))


def test_all_podstawowy_lists_only_coded_podstawowy_topics(db):
    from zaspro.knowledge.run import _all_podstawowy

    build_world(db)
    codes = [c for c, _, _ in _all_podstawowy(db)]
    assert {"VIII.1", "VIII.2", "VIII.3"} <= set(codes)
    assert "VIII.R1" not in codes
    assert codes == sorted(codes)
