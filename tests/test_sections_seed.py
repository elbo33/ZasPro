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


def test_reseed_drops_the_review_card_of_a_removed_section(db):
    from zaspro.db.models import (
        ReviewItem, ReviewItemType, ReviewStatus, Section,
    )

    _seed(db)
    sec = db.query(Section).filter_by(slug="twierdzenie-talesa").one()
    card = ReviewItem(
        item_type=ReviewItemType.KNOWLEDGE_SPEC, ref_table="sections",
        ref_id=sec.id, status=ReviewStatus.APPROVED, risk=0.5, title="x",
    )
    db.add(card)
    db.flush()
    old_id = sec.id

    # a seed where that slug is gone
    from pathlib import Path
    import yaml
    data = yaml.safe_load(
        (Path(__file__).resolve().parents[1] / "seeds" / "teaching_sections.yaml")
        .read_text(encoding="utf-8")
    )
    data["sections"] = [s for s in data["sections"] if s["slug"] != "twierdzenie-talesa"]
    # give VIII.7 a home so coverage still holds
    data["sections"][0]["requirements"] = list(data["sections"][0]["requirements"]) + ["VIII.7"]
    p = db.get(Section, old_id)  # keep a handle
    import tempfile
    f = Path(tempfile.mkstemp(suffix=".yaml")[1])
    f.write_text(yaml.safe_dump(data))

    seed_sections(db, f)
    assert db.get(Section, old_id) is None
    assert db.query(ReviewItem).filter_by(id=card.id).one_or_none() is None


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
