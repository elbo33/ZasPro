"""Small idempotent upsert helper. Seeding must be re-runnable (SPEC M1)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

from zaspro.db.base import Base

T = TypeVar("T", bound=Base)


@dataclass
class Counts:
    created: int = 0
    updated: int = 0
    unchanged: int = 0

    def record(self, outcome: str) -> None:
        setattr(self, outcome, getattr(self, outcome) + 1)

    def __str__(self) -> str:
        return f"{self.created} created, {self.updated} updated, {self.unchanged} unchanged"


def upsert(
    session: Session,
    model: type[T],
    *,
    key: dict[str, Any],
    values: dict[str, Any],
) -> tuple[T, str]:
    """Find *model* by *key*; sync *values*; create if missing.

    Returns (instance, "created" | "updated" | "unchanged").
    """

    stmt = select(model).filter_by(**key)
    obj = session.scalars(stmt).one_or_none()
    if obj is None:
        obj = model(**key, **values)
        session.add(obj)
        session.flush()
        return obj, "created"

    changed = False
    for attr, want in values.items():
        if getattr(obj, attr) != want:
            setattr(obj, attr, want)
            changed = True
    if changed:
        session.flush()
    return obj, "updated" if changed else "unchanged"
