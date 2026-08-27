"""Request-scoped dependencies. Kept separate from `app.py` so routers can
import it without pulling in app construction (circular import)."""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy.orm import Session

from zaspro.db.base import get_sessionmaker


def get_db() -> Iterator[Session]:
    session = get_sessionmaker()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
