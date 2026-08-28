"""Export an approved section's knowledge spec to a committed git file.

ADR 0012: git holds the record, the database is the working store. Once a
section's KNOWLEDGE_SPEC review card is resolved, its approved items are written
to `knowledge/sections/<slug>.yaml` — human-readable, diffable, one file per
section. That file is the freeze: `write_section` refuses to re-run a section
that has one unless `force=True`.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from sqlalchemy import select
from sqlalchemy.orm import Session

from zaspro.db.base import session_scope
from zaspro.db.models import (
    Concept, Example, Formula, LearningObjective, Method, Misconception,
    ReviewItem, ReviewItemType, ReviewStatus, Section, SectionSpec, Topic,
    VerificationStatus,
)

KNOWLEDGE_ROOT = Path("knowledge/sections")


class ExportError(RuntimeError):
    pass


def export_path(slug: str) -> Path:
    return KNOWLEDGE_ROOT / f"{slug}.yaml"


def is_frozen(slug: str | None) -> bool:
    return bool(slug) and export_path(slug).exists()


def _approved(session: Session, model: type, section_id: int) -> list:
    return list(
        session.scalars(
            select(model).where(
                model.section_id == section_id,
                model.verification_status == VerificationStatus.APPROVED,
            ).order_by(model.order_index, model.id)
        )
    )


def _fields(item: Any, names: list[str]) -> dict:
    d: dict[str, Any] = {}
    for n in names:
        v = getattr(item, n, None)
        if v not in (None, "", [], {}):
            d[n] = v
    return d


def build_export(session: Session, section_id: int) -> dict:
    section = session.get(Section, section_id)
    if section is None:
        raise ExportError(f"section {section_id} not found")
    spec = session.scalars(
        select(SectionSpec).where(SectionSpec.section_id == section_id)
    ).one_or_none()
    if spec is None:
        raise ExportError(f"{section.slug}: no spec on record — run knowledge.write first")

    codes = sorted(
        session.get(Topic, sr.topic_id).official_requirement_code
        for sr in section.requirements
    )
    return {
        "section": section.slug,
        "name": section.name,
        "scope": section.scope,
        "requirements": codes,
        "spec": {
            "agent": spec.agent_name,
            "model": spec.model,
            "prompt_version": spec.prompt_version,
            "written_at": spec.written_at.isoformat() if spec.written_at else None,
            "approved_at": spec.approved_at.isoformat() if spec.approved_at else None,
            "approved_by": spec.approved_by,
        },
        "concepts": [
            _fields(c, ["name", "description", "explanation", "difficulty"])
            for c in _approved(session, Concept, section_id)
        ],
        "formulas": [
            _fields(f, ["name", "latex_raw", "conditions", "description"])
            for f in _approved(session, Formula, section_id)
        ],
        "methods": [
            _fields(m, ["name", "when_to_use", "steps"])
            for m in _approved(session, Method, section_id)
        ],
        "examples": [
            _fields(e, ["statement", "worked_solution", "difficulty"])
            for e in _approved(session, Example, section_id)
        ],
        "objectives": [
            _fields(o, ["statement", "bloom_level"])
            for o in _approved(session, LearningObjective, section_id)
        ],
        "misconceptions": [
            _fields(mc, ["name", "incorrect_reasoning", "correct_reasoning", "severity"])
            for mc in _approved(session, Misconception, section_id)
        ],
    }


class _Dumper(yaml.SafeDumper):
    pass


def _str_representer(dumper: yaml.Dumper, value: str):
    style = "|" if "\n" in value else None
    return dumper.represent_scalar("tag:yaml.org,2002:str", value, style=style)


_Dumper.add_representer(str, _str_representer)


def dump_yaml(data: dict) -> str:
    return yaml.dump(data, Dumper=_Dumper, sort_keys=False, allow_unicode=True, width=100)


def _review_item(session: Session, section_id: int) -> ReviewItem | None:
    return session.scalars(
        select(ReviewItem).where(
            ReviewItem.item_type == ReviewItemType.KNOWLEDGE_SPEC,
            ReviewItem.ref_table == "sections",
            ReviewItem.ref_id == section_id,
        )
    ).one_or_none()


def export_section(session: Session, section_id: int, *, reviewer: str | None = None,
                   force_unreviewed: bool = False) -> Path:
    section = session.get(Section, section_id)
    if section is None:
        raise ExportError(f"section {section_id} not found")

    ri = _review_item(session, section_id)
    if not force_unreviewed:
        if ri is None:
            raise ExportError(f"{section.slug}: no review card — nothing reviewed")
        if ri.status is ReviewStatus.OPEN:
            raise ExportError(f"{section.slug}: review card is still OPEN — approve it first")
        if ri.status is ReviewStatus.REJECTED:
            raise ExportError(f"{section.slug}: review card was REJECTED — not an approved spec")

    data = build_export(session, section_id)
    path = export_path(section.slug)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dump_yaml(data), encoding="utf-8")

    spec = session.scalars(
        select(SectionSpec).where(SectionSpec.section_id == section_id)
    ).one_or_none()
    if spec is not None:
        now = datetime.now(timezone.utc)
        spec.exported_at = now
        spec.export_path = str(path)
        if spec.approved_at is None:
            spec.approved_at = now
        if reviewer and not spec.approved_by:
            spec.approved_by = reviewer
        session.flush()
    return path


def load_export(slug: str) -> dict:
    return yaml.safe_load(export_path(slug).read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- #

def _main(argv: list[str]) -> int:
    force = "--force-unreviewed" in argv
    do_all = "--all" in argv
    slugs = [a for a in argv if not a.startswith("-")]
    with session_scope() as s:
        if do_all:
            targets = list(s.scalars(select(Section).order_by(Section.order_index)))
        elif slugs:
            targets = list(s.scalars(select(Section).where(Section.slug.in_(slugs))))
        else:
            print("usage: python -m zaspro.knowledge.export <slug...> | --all")
            return 2

        wrote = skipped = failed = 0
        for section in targets:
            try:
                path = export_section(s, section.id, force_unreviewed=force)
                print(f"  wrote {path}")
                wrote += 1
            except ExportError as e:
                if do_all:
                    skipped += 1
                else:
                    print(f"  SKIP {section.slug}: {e}")
                    failed += 1
        print(f"\n{wrote} exported"
              + (f", {skipped} not ready" if do_all else "")
              + (f", {failed} failed" if failed else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
