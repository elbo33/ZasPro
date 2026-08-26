"""Curriculum hierarchy — synthetic 3-topic fixture (SPEC §18) + the real seed."""

import pytest
from sqlalchemy.exc import IntegrityError

from zaspro.db.models import Subject, Topic, TopicLevel, Unit


@pytest.fixture
def mini_tree(db):
    subject = Subject(name="Test", slug="test", level="podstawowy, rozszerzony")
    unit = Unit(subject=subject, code="T1", slug="t1", name="Test unit", order_index=1)
    a = Topic(
        unit=unit, name="topic a", slug="t-1", level=TopicLevel.PODSTAWOWY,
        order_index=1, official_requirement_code="T1.1",
    )
    b = Topic(
        unit=unit, name="topic b", slug="t-2", level=TopicLevel.PODSTAWOWY,
        order_index=2, official_requirement_code="T1.2",
    )
    c = Topic(
        unit=unit, name="topic c", slug="t-r1", level=TopicLevel.ROZSZERZONY,
        order_index=1, official_requirement_code="T1.R1",
    )
    db.add(subject)
    db.flush()
    return subject, unit, (a, b, c)


def test_hierarchy_wiring_and_order(db, mini_tree):
    subject, unit, (a, b, c) = mini_tree
    db.expire_all()

    assert [u.code for u in subject.units] == ["T1"]
    # topics come back podstawowy-then-rozszerzony, each block by order_index
    assert [t.official_requirement_code for t in unit.topics] == ["T1.1", "T1.2", "T1.R1"]
    assert a.unit is unit and c.unit.subject is subject


def test_official_requirement_code_is_unique(db, mini_tree):
    _, unit, _ = mini_tree
    db.add(Topic(
        unit=unit, name="dup", slug="dup", level=TopicLevel.PODSTAWOWY,
        order_index=9, official_requirement_code="T1.1",
    ))
    with pytest.raises(IntegrityError):
        db.flush()


def test_adjacency_list_parent_child(db, mini_tree):
    _, _, (a, b, c) = mini_tree
    c.parent = a
    db.flush()
    db.expire_all()
    assert c.parent is a
    assert c in a.children


def test_real_seed_shape(db):
    from zaspro.seeding.curriculum import seed_curriculum

    seed_curriculum(db)
    db.flush()

    subj = db.query(Subject).filter_by(slug="matematyka").one()
    assert len(subj.units) == 13
    topics = db.query(Topic).all()
    assert len(topics) == 119
    assert sum(t.level == TopicLevel.PODSTAWOWY for t in topics) == 73
    assert sum(t.statement_latex is not None for t in topics) == 20
    # every topic has its official code and belongs to a unit
    assert all(t.official_requirement_code and t.unit_id for t in topics)
