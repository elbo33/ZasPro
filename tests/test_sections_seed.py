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
    assert counts.created == 50

    n_pod = db.query(Topic).filter(
        Topic.level == TopicLevel.PODSTAWOWY,
        Topic.official_requirement_code.is_not(None),
    ).count()
    assert db.query(SectionRequirement).count() == n_pod == 73

    # a requirement is in exactly one section
    topic_ids = [sr.topic_id for sr in db.query(SectionRequirement)]
    assert len(topic_ids) == len(set(topic_ids))


def test_seed_is_idempotent(db):
    _seed(db)
    counts = seed_sections(db)
    assert counts.created == 0 and counts.updated == 0
    assert db.query(Section).count() == 50


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
