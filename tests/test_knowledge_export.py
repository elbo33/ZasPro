"""Knowledge export to committed files + the review-gated freeze (M4, ADR 0011)."""

from __future__ import annotations

import pytest

from tests.fixtures.mapping_world import build_world
from zaspro.db.models import (
    Concept, ExerciseTopic, Misconception, MisconceptionSource, ReviewDecisionType,
    ReviewReasonCode, TopicRole, VerificationStatus,
)
from zaspro.knowledge import export as kexport
from zaspro.knowledge.agent import ConceptOut, KnowledgeExtraction, MisconceptionOut
from zaspro.knowledge.export import ExportError, export_topic, is_frozen, load_export
from zaspro.knowledge.extract import extract_topic
from zaspro.review.queue import record_decision


@pytest.fixture(autouse=True)
def _kroot(tmp_path, monkeypatch):
    monkeypatch.setattr(kexport, "KNOWLEDGE_ROOT", tmp_path / "knowledge" / "topics")


def _extract(db):
    w = build_world(db)
    for num in ("1", "4"):
        from zaspro.db.models import Exercise
        ex = db.query(Exercise).filter_by(
            source_document_id=w.document_id, exercise_number=num
        ).one()
        db.add(ExerciseTopic(exercise_id=ex.id, topic_id=w.topic_ids["VIII.2"],
                             role=TopicRole.PRIMARY, confidence=0.9))
    db.flush()

    class A:
        name, model, prompt_version = "fake", "claude-opus-5", "m4-know-v3"
        last_usage = None

        def extract(self, request):
            return KnowledgeExtraction(
                concepts=[
                    ConceptOut(name="Pythagoras", description="a^2+b^2=c^2",
                               from_exercises=["1"], evidence="Zad 1"),
                ],
                misconceptions=[
                    MisconceptionOut(
                        name="adds the legs", incorrect_reasoning="a+b=c",
                        correct_reasoning="square them",
                        source_kind=MisconceptionSource.AGENT_INFERENCE,
                        from_exercises=["1"], evidence="Zad 1 slip",
                    ),
                ],
            )
    res = extract_topic(db, w.topic_ids["VIII.2"], A())
    return w, res


def test_export_refuses_while_the_review_card_is_open(db):
    w, res = _extract(db)
    with pytest.raises(ExportError):
        export_topic(db, w.topic_ids["VIII.2"])
    assert not is_frozen("VIII.2")


def test_approved_topic_exports_only_approved_items_and_freezes(db):
    w, res = _extract(db)
    # reject the misconception inline, then approve the card
    mc = db.query(Misconception).one()
    record_decision(db, res.review_item_id, reviewer="elie",
                    decision=ReviewDecisionType.EDIT,
                    edit={"reject_items": [["misconception", mc.id]]})
    record_decision(db, res.review_item_id, reviewer="elie",
                    decision=ReviewDecisionType.APPROVE)

    path = export_topic(db, w.topic_ids["VIII.2"], reviewer="elie")
    assert path.exists() and is_frozen("VIII.2")

    data = load_export("VIII.2")
    assert data["requirement_code"] == "VIII.2"
    assert [c["name"] for c in data["concepts"]] == ["Pythagoras"]
    assert data["misconceptions"] == []          # the rejected one is not in the file
    assert data["extraction"]["approved_by"] == "elie"
    assert {e["number"] for e in data["exercises"]} == {"1", "4"}

    # the DB row is stamped
    from zaspro.db.models import KnowledgeExtraction as KERow
    ke = db.query(KERow).filter_by(topic_id=w.topic_ids["VIII.2"]).one()
    assert ke.exported_at is not None and ke.export_path == str(path)


def test_reject_card_marks_every_item_rejected(db):
    w, res = _extract(db)
    record_decision(db, res.review_item_id, reviewer="elie",
                    decision=ReviewDecisionType.REJECT,
                    reason_code=ReviewReasonCode.OTHER)
    assert db.query(Concept).one().verification_status is VerificationStatus.REJECTED
    assert db.query(Misconception).one().verification_status is VerificationStatus.REJECTED
    with pytest.raises(ExportError):
        export_topic(db, w.topic_ids["VIII.2"])
