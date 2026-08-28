"""write_section: persistence, the section review card, and the freeze (M4)."""

from __future__ import annotations

import pytest

from tests.fixtures.mapping_world import build_world
from zaspro.db.models import (
    Concept, Example, Method, ReviewItem, ReviewItemType, ReviewStatus, Section,
    SectionRequirement, SectionSpec,
)
from zaspro.knowledge import export as kexport
from zaspro.knowledge.agent import (
    ConceptOut, ExampleOut, MethodOut, MisconceptionOut, ObjectiveOut,
    SectionSpecOut,
)
from zaspro.knowledge.write import KnowledgeFrozen, write_section


@pytest.fixture(autouse=True)
def _kroot(tmp_path, monkeypatch):
    monkeypatch.setattr(kexport, "KNOWLEDGE_ROOT", tmp_path / "knowledge" / "sections")


def _section(db, slug="planimetria-okrag"):
    w = build_world(db)
    subj_id = db.query(Section).first()  # none yet
    from zaspro.db.models import Subject
    subject = db.query(Subject).one()
    sec = Section(subject_id=subject.id, slug=slug, name="Okrąg — testowa sekcja",
                  scope="circles and chords", order_index=1)
    db.add(sec)
    db.flush()
    for code in ("VIII.1", "VIII.2"):
        db.add(SectionRequirement(section_id=sec.id, topic_id=w.topic_ids[code]))
    db.flush()
    return sec


def _agent(spec: SectionSpecOut):
    class A:
        name, model, prompt_version = "fake", None, "m4-sec-v1"
        last_usage = None

        def write(self, request):
            self.request = request
            return spec
    return A()


_FULL = SectionSpecOut(
    concepts=[ConceptOut(name="chord", definition="a segment between two points on a circle")],
    formulas=[],
    methods=[MethodOut(name="use Pythagoras", when_to_use="radius, chord, distance",
                       steps=["drop a perpendicular", "solve the right triangle"])],
    examples=[ExampleOut(statement="easy", worked_solution="...", difficulty=1),
              ExampleOut(statement="harder", worked_solution="...", difficulty=3)],
    misconceptions=[MisconceptionOut(name="tangent isn't perpendicular",
                                     incorrect_reasoning="x", correct_reasoning="y")],
    objectives=[ObjectiveOut(statement="find a chord length", bloom_level="apply")],
)


def test_write_persists_items_and_opens_one_review_card(db):
    sec = _section(db)
    res = write_section(db, sec.id, _agent(_FULL))
    assert (res.concepts, res.methods, res.examples, res.misconceptions, res.objectives) == (1, 1, 2, 1, 1)

    ri = db.query(ReviewItem).filter_by(item_type=ReviewItemType.KNOWLEDGE_SPEC).one()
    assert ri.ref_table == "sections" and ri.ref_id == sec.id and ri.status is ReviewStatus.OPEN

    spec = db.query(SectionSpec).filter_by(section_id=sec.id).one()
    assert spec.agent_name == "fake" and spec.review_item_id == ri.id
    assert db.query(Example).filter_by(section_id=sec.id).count() == 2
    assert [c.order_index for c in db.query(Concept).filter_by(section_id=sec.id)] == [0]


def test_the_agent_request_carries_the_section_scope_and_codes(db):
    sec = _section(db)
    a = _agent(_FULL)
    write_section(db, sec.id, a)
    assert a.request.scope == "circles and chords"
    assert sorted(r.code for r in a.request.requirements) == ["VIII.1", "VIII.2"]


def test_rewrite_replaces_prior_items_and_reopens_the_card(db):
    sec = _section(db)
    res = write_section(db, sec.id, _agent(_FULL))
    from zaspro.db.models import ReviewReasonCode
    from zaspro.review.queue import record_decision, ReviewDecisionType
    record_decision(db, res.review_item_id, reviewer="e",
                    decision=ReviewDecisionType.REJECT, reason_code=ReviewReasonCode.OTHER)

    write_section(db, sec.id, _agent(SectionSpecOut()))
    assert db.query(Method).filter_by(section_id=sec.id).count() == 0
    assert db.query(ReviewItem).filter_by(
        item_type=ReviewItemType.KNOWLEDGE_SPEC
    ).one().status is ReviewStatus.OPEN


def test_frozen_section_refuses_rewrite_without_force(db):
    sec = _section(db, slug="frozen-sec")
    a = _agent(SectionSpecOut())
    write_section(db, sec.id, a)

    kexport.KNOWLEDGE_ROOT.mkdir(parents=True, exist_ok=True)
    kexport.export_path("frozen-sec").write_text("section: frozen-sec\n")

    with pytest.raises(KnowledgeFrozen):
        write_section(db, sec.id, a)
    write_section(db, sec.id, a, force=True)
