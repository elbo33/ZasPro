"""Seeding is idempotent and re-runnable (SPEC M1)."""

from sqlalchemy import func, select

from zaspro.db.models import Source, Subject, Topic, Unit
from zaspro.seeding.curriculum import seed_curriculum
from zaspro.seeding.manifest import load_manifest
from zaspro.seeding.sources import seed_sources

N_SOURCES = len(load_manifest())  # tracks the manifest as the corpus grows
N_CURRICULUM = 133  # 1 subject + 13 units + 119 topics


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
    assert (c.created, c.updated, c.unchanged) == (N_CURRICULUM, 0, 0)
    assert (s.created, s.updated, s.unchanged) == (N_SOURCES, 0, 0)
    assert _counts(db) == (1, 13, 119, N_SOURCES)


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
    assert c.unchanged == N_CURRICULUM and s.unchanged == N_SOURCES
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
