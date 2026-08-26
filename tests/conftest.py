"""Test fixtures. DB-backed tests target a dedicated `zaspro_test` database and
skip cleanly when PostgreSQL is not reachable (SPEC §18: no network needed —
this is a local DB, but it is still optional infrastructure)."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

HAVE_PANDOC = shutil.which("pandoc") is not None
HAVE_SOFFICE = (
    shutil.which("soffice")
    or shutil.which("libreoffice")
    or Path("/Applications/LibreOffice.app/Contents/MacOS/soffice").is_file()
)
needs_pandoc = pytest.mark.skipif(not HAVE_PANDOC, reason="pandoc not installed")
needs_soffice = pytest.mark.skipif(not HAVE_SOFFICE, reason="LibreOffice not installed")

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://zaspro:zaspro@localhost:5432/zaspro_test",
)

_url = make_url(TEST_DATABASE_URL)
assert _url.database and "test" in _url.database, (
    f"refusing to run DB tests against {_url.database!r}: name must contain 'test'"
)

# Point the whole app at the test DB before anything imports zaspro.config.
os.environ["DATABASE_URL"] = TEST_DATABASE_URL

_ALL_TABLES = "subjects, units, topics, topic_prerequisites, sources"


def _postgres_reachable() -> bool:
    try:
        eng = create_engine(_url.set(database="postgres"), connect_args={"connect_timeout": 2})
        with eng.connect():
            pass
        eng.dispose()
        return True
    except Exception:
        return False


@pytest.fixture(scope="session")
def migrated_db():
    if not _postgres_reachable():
        pytest.skip("PostgreSQL not reachable — start it with `docker compose up -d db`")

    admin = create_engine(_url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :n"), {"n": _url.database}
        ).scalar()
        if not exists:
            conn.execute(text(f'CREATE DATABASE "{_url.database}"'))
    admin.dispose()

    from alembic import command
    from alembic.config import Config

    command.upgrade(Config("alembic.ini"), "head")
    yield


_ALL_TABLES_M2 = _ALL_TABLES + ", source_documents, source_chunks, figures, exercises, exercise_figures, jobs"


@pytest.fixture
def db(migrated_db):
    """A clean session per test: every table truncated, changes rolled back."""

    from zaspro.db.base import get_engine, get_sessionmaker

    with get_engine().begin() as conn:
        conn.execute(text(f"TRUNCATE {_ALL_TABLES_M2} RESTART IDENTITY CASCADE"))

    session = get_sessionmaker()()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def mini_docx(tmp_path):
    """A tiny synthetic arkusz .docx (no real source material)."""

    from tests.fixtures.synthetic import build_mini_arkusz_docx

    return build_mini_arkusz_docx(tmp_path / "mini-arkusz.docx")
