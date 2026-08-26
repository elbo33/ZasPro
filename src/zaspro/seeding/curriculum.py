"""Seed the curriculum tree from the hand-verified M0.6 seed file.

`seeds/curriculum_matematyka.yaml` is the authority (STATUS: VERIFIED). This
loads it as-is: units in Dz.U. order, topics as podstawowy then rozszerzony
within each unit, `statement_latex` where the requirement carries a formula.
Sub-points (I.2 a/b, XI.2 a/b) are comments in the seed, not nodes.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from sqlalchemy.orm import Session

from zaspro.db.models import Subject, Topic, TopicLevel, Unit
from zaspro.seeding.slugs import slugify
from zaspro.seeding.upsert import Counts, upsert

ROOT = Path(__file__).resolve().parents[3]
SEED = ROOT / "seeds" / "curriculum_matematyka.yaml"

_LEVEL = {"podstawowy": TopicLevel.PODSTAWOWY, "rozszerzony": TopicLevel.ROZSZERZONY}


def seed_curriculum(session: Session, seed_path: Path = SEED) -> Counts:
    data = yaml.safe_load(seed_path.read_text(encoding="utf-8"))
    subj = data["subject"]
    counts = Counts()

    subject, outcome = upsert(
        session,
        Subject,
        key={"slug": subj["slug"]},
        values={
            "name": subj["name"],
            "language": subj.get("language", "pl"),
            "level": ", ".join(subj["levels"]),
        },
    )
    counts.record(outcome)

    for order, unit_row in enumerate(data["units"], start=1):
        unit, outcome = upsert(
            session,
            Unit,
            key={"subject_id": subject.id, "code": unit_row["code"]},
            values={
                "name": unit_row["name"],
                "slug": slugify(unit_row["name"]),
                "order_index": order,
            },
        )
        counts.record(outcome)

        # order_index runs 1..n within (unit, level) — the regulation's own order
        seq: dict[TopicLevel, int] = {}
        for topic_row in unit_row["topics"]:
            level = _LEVEL[topic_row["level"]]
            seq[level] = seq.get(level, 0) + 1
            code = topic_row["code"]
            _, outcome = upsert(
                session,
                Topic,
                key={"official_requirement_code": code},
                values={
                    "unit_id": unit.id,
                    "name": topic_row["name"],
                    "slug": slugify(code),
                    "statement_latex": topic_row.get("statement_latex"),
                    "level": level,
                    "order_index": seq[level],
                },
            )
            counts.record(outcome)

    return counts
