"""Seed the database. Idempotent — safe to run repeatedly.

    uv run python -m zaspro.seeding.run

Requires the schema to be migrated first (`uv run alembic upgrade head`).
"""

from __future__ import annotations

import sys

from zaspro.db.base import session_scope
from zaspro.seeding.curriculum import seed_curriculum
from zaspro.seeding.sources import seed_sources


def run() -> int:
    with session_scope() as session:
        curr = seed_curriculum(session)
        src = seed_sources(session)
    print(f"curriculum : {curr}")
    print(f"sources    : {src}")
    return 0


if __name__ == "__main__":
    sys.exit(run())
