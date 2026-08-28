"""Section spec export to git + the review-gated freeze (M4, ADR 0012)."""

from __future__ import annotations

import pytest

from tests.fixtures.mapping_world import build_world
from zaspro.db.models import (
    Concept, Misconception, ReviewDecisionType, ReviewReasonCode, Section,
    SectionRequirement, SectionSpec, Subject, VerificationStatus,
)
from zaspro.knowledge import export as kexport
from zaspro.knowledge.agent import ConceptOut, MisconceptionOut, SectionSpecOut
from zaspro.knowledge.export import (
    ExportError, export_section, is_frozen, load_export,
)
from zaspro.knowledge.write import write_section
from zaspro.review.queue import record_decision


@pytest.fixture(autouse=True)
def _kroot(tmp_path, monkeypatch):
    monkeypatch.setattr(kexport, "KNOWLEDGE_ROOT", tmp_path / "knowledge" / "sections")


def _written(db):
    w = build_world(db)
    subject = db.query(Subject).one()
    sec = Section(subject_id=subject.id, slug="funkcja-liniowa", name="Funkcja liniowa",
                  scope="the linear function", order_index=1)
    db.add(sec)
    db.flush()
    db.add(SectionRequirement(section_id=sec.id, topic_id=w.topic_ids["VIII.1"]))
    db.flush()

    class A:
        name, model, prompt_version = "fake", "claude-opus-5", "m4-sec-v1"
        last_usage = None

        def write(self, request):
            return SectionSpecOut(
                concepts=[ConceptOut(name="slope", definition="rise over run")],
                misconceptions=[MisconceptionOut(name="confuses a and b",
                                                 incorrect_reasoning="x", correct_reasoning="y")],
            )
    res = write_section(db, sec.id, A())
    return sec, res


def test_export_refuses_while_the_card_is_open(db):
    sec, res = _written(db)
    with pytest.raises(ExportError):
        export_section(db, sec.id)
    assert not is_frozen("funkcja-liniowa")


def test_approved_section_exports_only_approved_items_and_freezes(db):
    sec, res = _written(db)
    mc = db.query(Misconception).one()
    record_decision(db, res.review_item_id, reviewer="elie",
                    decision=ReviewDecisionType.EDIT,
                    edit={"reject_items": [["misconception", mc.id]]})
    record_decision(db, res.review_item_id, reviewer="elie",
                    decision=ReviewDecisionType.APPROVE)

    path = export_section(db, sec.id, reviewer="elie")
    assert path.exists() and is_frozen("funkcja-liniowa")

    data = load_export("funkcja-liniowa")
    assert data["section"] == "funkcja-liniowa"
    assert data["requirements"] == ["VIII.1"]
    assert [c["name"] for c in data["concepts"]] == ["slope"]
    assert data["misconceptions"] == []            # the rejected one is gone
    assert data["spec"]["approved_by"] == "elie"

    spec = db.query(SectionSpec).filter_by(section_id=sec.id).one()
    assert spec.exported_at is not None and spec.export_path == str(path)


def test_reject_card_marks_every_item_rejected(db):
    sec, res = _written(db)
    record_decision(db, res.review_item_id, reviewer="elie",
                    decision=ReviewDecisionType.REJECT, reason_code=ReviewReasonCode.OTHER)
    assert db.query(Concept).one().verification_status is VerificationStatus.REJECTED
    with pytest.raises(ExportError):
        export_section(db, sec.id)
