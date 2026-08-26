"""topic_prerequisites is a DAG — the write-time trigger rejects cycles (SPEC §5)."""

import pytest
from sqlalchemy.exc import IntegrityError

from zaspro.db.models import Subject, Topic, TopicLevel, TopicPrerequisite, Unit


@pytest.fixture
def topics(db):
    s = Subject(name="T", slug="t", level="podstawowy")
    u = Unit(subject=s, code="U", slug="u", name="U", order_index=1)
    made = {}
    for i, code in enumerate("ABCD", start=1):
        made[code] = Topic(
            unit=u, name=code, slug=code.lower(), level=TopicLevel.PODSTAWOWY,
            order_index=i, official_requirement_code=f"U.{i}",
        )
    db.add(s)
    db.flush()
    return made


def _edge(db, a: Topic, b: Topic) -> None:
    db.add(TopicPrerequisite(topic_id=a.id, prerequisite_topic_id=b.id))
    db.flush()


def test_a_valid_dag_is_accepted(db, topics):
    A, B, C, D = topics["A"], topics["B"], topics["C"], topics["D"]
    _edge(db, A, B)  # A needs B
    _edge(db, A, C)
    _edge(db, B, C)
    _edge(db, C, D)
    assert db.query(TopicPrerequisite).count() == 4


def test_direct_two_node_cycle_is_rejected(db, topics):
    A, B = topics["A"], topics["B"]
    _edge(db, A, B)
    with pytest.raises(IntegrityError, match="cycle"):
        _edge(db, B, A)


def test_deliberate_three_node_loop_is_rejected(db, topics):
    A, B, C = topics["A"], topics["B"], topics["C"]
    _edge(db, A, B)
    _edge(db, B, C)
    with pytest.raises(IntegrityError, match="cycle"):
        _edge(db, C, A)  # closes A -> B -> C -> A


def test_self_prerequisite_is_rejected(db, topics):
    A = topics["A"]
    with pytest.raises(IntegrityError):
        _edge(db, A, A)  # CHECK constraint, before the trigger
