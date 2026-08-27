"""Knowledge extraction: business rules + misconception source handling (M4)."""

from __future__ import annotations

from tests.fixtures.mapping_world import build_world
from zaspro.db.models import (
    ChunkMapping, ContentType, ExerciseTopic, KnowledgeFlag, MappingStatus,
    Misconception, MisconceptionSource, TopicRole,
)
from zaspro.knowledge.agent import (
    ConceptOut, KnowledgeExtraction, MisconceptionOut, MethodOut,
)
from zaspro.knowledge.extract import extract_topic


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
