"""seed_sections: idempotent, and covers every podstawowy requirement once."""

from __future__ import annotations

import pytest

from zaspro.db.models import Section, SectionRequirement, Topic, TopicLevel
from zaspro.seeding.curriculum import seed_curriculum
from zaspro.seeding.sections import seed_sections


def _seed(db):
    seed_curriculum(db)
    return seed_sections(db)


def test_seed_covers_all_podstawowy_requirements_exactly_once(db):
    counts = _seed(db)
    n_sections = db.query(Section).count()
    assert counts.created == n_sections

    n_pod = db.query(Topic).filter(
        Topic.level == TopicLevel.PODSTAWOWY,
        Topic.official_requirement_code.is_not(None),
    ).count()
    assert db.query(SectionRequirement).count() == n_pod == 73

    # a requirement is in exactly one section; order is a permutation of 1..N
    topic_ids = [sr.topic_id for sr in db.query(SectionRequirement)]
    assert len(topic_ids) == len(set(topic_ids))
    orders = sorted(s.order_index for s in db.query(Section))
    assert orders == list(range(1, n_sections + 1))


def test_seed_is_idempotent_and_reorders_without_collision(db):
    _seed(db)
    n = db.query(Section).count()
    counts = seed_sections(db)  # re-run: parks order_index, resyncs
    assert counts.created == 0
    assert db.query(Section).count() == n


def test_seed_rejects_a_missing_requirement(db, tmp_path):
    seed_curriculum(db)
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        "subject: matematyka\n"
        "sections:\n"
        "  - slug: only-one\n"
        "    name: n\n"
        "    scope: s\n"
        "    requirements: [I.1]\n"
    )
    with pytest.raises(ValueError, match="not covered"):
        seed_sections(db, bad)
