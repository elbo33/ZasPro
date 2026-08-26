"""Seeding is idempotent and re-runnable (SPEC M1)."""

from sqlalchemy import func, select

from zaspro.db.models import Source, Subject, Topic, Unit
from zaspro.seeding.curriculum import seed_curriculum
from zaspro.seeding.sources import seed_sources


def _counts(db) -> tuple[int, int, int, int]:
    return (
        db.scalar(select(func.count()).select_from(Subject)),
        db.scalar(select(func.count()).select_from(Unit)),
        db.scalar(select(func.count()).select_from(Topic)),
        db.scalar(select(func.count()).select_from(Source)),
    )


def test_first_run_creates_everything(db):
    c = seed_curriculum(db)
    s = seed_sources(db)
    db.flush()
    assert (c.created, c.updated, c.unchanged) == (133, 0, 0)  # 1 + 13 + 119
    assert (s.created, s.updated, s.unchanged) == (8, 0, 0)
    assert _counts(db) == (1, 13, 119, 8)


def test_second_run_is_a_noop(db):
    seed_curriculum(db)
    seed_sources(db)
    db.flush()
    before = _counts(db)

    c = seed_curriculum(db)
    s = seed_sources(db)
    db.flush()

    assert (c.created, c.updated) == (0, 0)
    assert (s.created, s.updated) == (0, 0)
    assert c.unchanged == 133 and s.unchanged == 8
    assert _counts(db) == before


def test_reseed_repairs_a_drifted_row(db):
    seed_curriculum(db)
    db.flush()
    topic = db.scalars(select(Topic).filter_by(official_requirement_code="VII.3")).one()
    topic.name = "corrupted"
    topic.statement_latex = None
    db.flush()

    c = seed_curriculum(db)
    db.flush()
    db.refresh(topic)

    assert c.updated == 1
    assert topic.name.startswith("stosuje twierdzenie cosinus")
    assert topic.statement_latex == r"P = \tfrac{1}{2} \cdot a \cdot b \cdot \sin\gamma"
