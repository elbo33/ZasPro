"""Seed the teaching sections from `seeds/teaching_sections.yaml`.

Idempotent. Asserts that the sections cover every podstawowy
`official_requirement_code` exactly once — coverage against the podstawa stays
provable (ADR 0012).
"""

from __future__ import annotations

from pathlib import Path

import yaml
from sqlalchemy import select
from sqlalchemy.orm import Session

from zaspro.db.models import (
    Section, SectionRequirement, Subject, Topic, TopicLevel,
)
from zaspro.seeding.upsert import Counts, upsert

ROOT = Path(__file__).resolve().parents[3]
SEED = ROOT / "seeds" / "teaching_sections.yaml"


def seed_sections(session: Session, seed_path: Path = SEED) -> Counts:
    data = yaml.safe_load(seed_path.read_text(encoding="utf-8"))
    subject = session.scalars(
        select(Subject).where(Subject.slug == data["subject"])
    ).one()

    by_code = dict(
        session.execute(
            select(Topic.official_requirement_code, Topic.id).where(
                Topic.level == TopicLevel.PODSTAWOWY,
                Topic.official_requirement_code.is_not(None),
            )
        ).all()
    )

    counts = Counts()
    seen: dict[str, str] = {}  # code -> section slug (for the coverage assertion)
    seed_slugs: set[str] = set()

    for order, row in enumerate(data["sections"], start=1):
        seed_slugs.add(row["slug"])
        section, outcome = upsert(
            session, Section,
            key={"slug": row["slug"]},
            values={
                "subject_id": subject.id,
                "name": row["name"],
                "scope": row["scope"],
                "order_index": order,
            },
        )
        counts.record(outcome)

        want_topic_ids: set[int] = set()
        for code in row["requirements"]:
            if code not in by_code:
                raise ValueError(f"section {row['slug']}: unknown requirement {code!r}")
            if code in seen:
                raise ValueError(
                    f"requirement {code} is in two sections: {seen[code]} and {row['slug']}"
                )
            seen[code] = row["slug"]
            want_topic_ids.add(by_code[code])

        have = {sr.topic_id for sr in section.requirements}
        for tid in want_topic_ids - have:
            session.add(SectionRequirement(section_id=section.id, topic_id=tid))
        for sr in list(section.requirements):
            if sr.topic_id not in want_topic_ids:
                session.delete(sr)
        session.flush()

    # drop sections no longer in the seed
    for section in session.scalars(select(Section)):
        if section.slug not in seed_slugs:
            session.delete(section)
    session.flush()

    missing = set(by_code) - set(seen)
    if missing:
        raise ValueError(
            f"{len(missing)} podstawowy requirement(s) not covered by any section: "
            f"{sorted(missing)}"
        )
    return counts
