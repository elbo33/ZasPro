"""The M1 migration produces the expected schema and the models match it."""

from sqlalchemy import inspect, text


def test_migration_creates_the_m1_tables(db):
    tables = set(inspect(db.bind).get_table_names())
    assert {"subjects", "units", "topics", "topic_prerequisites", "sources"} <= tables


def test_prerequisite_cycle_trigger_exists(db):
    got = db.execute(
        text("SELECT tgname FROM pg_trigger WHERE NOT tgisinternal")
    ).scalars().all()
    assert "topic_prerequisites_no_cycle" in got


def test_no_pgvector_extension(db):
    # SPEC §15: pgvector is never added in a migration.
    ext = db.execute(text("SELECT extname FROM pg_extension")).scalars().all()
    assert "vector" not in ext


def test_models_and_schema_are_in_sync(db):
    """alembic autogenerate against the migrated DB must find nothing to do."""

    from alembic.autogenerate import compare_metadata
    from alembic.runtime.migration import MigrationContext

    import zaspro.db.models  # noqa: F401
    from zaspro.db.base import Base

    ctx = MigrationContext.configure(
        db.connection(), opts={"compare_type": True, "target_metadata": Base.metadata}
    )
    diff = compare_metadata(ctx, Base.metadata)
    assert diff == [], f"models drifted from migration 0001: {diff}"
