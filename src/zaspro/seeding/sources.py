"""Seed `sources` from `sources/MANIFEST.md`, verbatim.

SPEC M1: licensing metadata comes from the manifest, never a model. An
unrecognised `source_type` or `licence_status` fails here rather than being
coerced — the enums mirror the manifest's vocabulary.
"""

from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import Session

from zaspro.db.models import LicenceStatus, Source, SourceType
from zaspro.seeding.manifest import MANIFEST, load_manifest
from zaspro.seeding.upsert import Counts, upsert


def seed_sources(session: Session, manifest_path: Path = MANIFEST) -> Counts:
    counts = Counts()
    for row in load_manifest(manifest_path):
        try:
            source_type = SourceType(row.source_type)
        except ValueError as exc:
            raise ValueError(
                f"{row.file}: unknown source_type {row.source_type!r} — "
                "add it to SourceType or fix the manifest"
            ) from exc
        try:
            licence = LicenceStatus(row.licence_status)
        except ValueError as exc:
            raise ValueError(
                f"{row.file}: unknown licence_status {row.licence_status!r} — "
                "add it to LicenceStatus or fix the manifest"
            ) from exc

        _, outcome = upsert(
            session,
            Source,
            key={"file_ref": row.file},
            values={
                "title": row.title,
                "publisher": row.publisher,
                "source_type": source_type,
                "licence_status": licence,
                "verbatim_ok": row.verbatim_ok,
                "url": row.url,
                "notes": row.notes,
            },
        )
        counts.record(outcome)
    return counts
