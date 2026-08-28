"""Export an approved topic's knowledge layer to a committed git file.

ADR 0011: git holds the record, the database is the working store. Once a
topic's KNOWLEDGE_SPEC review card is resolved, its approved items are written
to `knowledge/topics/<official_requirement_code>.yaml` — human-readable,
diffable, one file per topic. That file is the freeze: `extract_topic` refuses
to re-run a topic that has one unless `force=True`.

The file carries everything needed to rebuild the DB rows (plus the source
documents, which M2 re-ingests): the extraction metadata, every approved
concept / formula / method / example / objective / misconception with its
evidence and cited exercises, the unresolved flags, and the touch-set exercise
index (numbers + source, not full text — that lives in the source documents).
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
    Concept, Example, Exercise, ExerciseTopic, Formula, KnowledgeExtraction,
    KnowledgeFlag, LearningObjective, Method, Misconception, ReviewItem,
    ReviewItemType, ReviewStatus, SourceChunk, SourceDocument, Topic,
    VerificationStatus,
)

KNOWLEDGE_ROOT = Path("knowledge/topics")


class ExportError(RuntimeError):
    pass


def export_path(code: str) -> Path:
    return KNOWLEDGE_ROOT / f"{code}.yaml"


def is_frozen(code: str | None) -> bool:
    """True once the topic has a committed export file — the 'generate once'
    lock. `extract_topic` checks this."""
    return bool(code) and export_path(code).exists()


def _approved(session: Session, model: type, topic_id: int) -> list:
    return list(
        session.scalars(
            select(model).where(
                model.topic_id == topic_id,
                model.verification_status == VerificationStatus.APPROVED,
            ).order_by(model.id)
        )
    )


def _chunk_number(session: Session, chunk_ids: list[int] | None) -> list[str]:
    """chunk ids -> their `Zadanie N.` numbers, for a stable human-readable ref."""
    if not chunk_ids:
        return []
    out: list[str] = []
    for cid in chunk_ids:
        c = session.get(SourceChunk, cid)
        if c is not None and c.heading and c.heading.startswith("Zadanie "):
            out.append(c.heading.removeprefix("Zadanie ").rstrip(". "))
    return out


def _item_dict(session: Session, item: Any, fields: list[str]) -> dict:
    d: dict[str, Any] = {}
    for f in fields:
        v = getattr(item, f, None)
        if v not in (None, "", [], {}):
            d[f] = v
    refs = _chunk_number(session, getattr(item, "source_chunk_ids", None))
    if refs:
        d["from_exercises"] = refs
    return d


def _exercise_index(session: Session, topic_id: int) -> list[dict]:
    rows = session.execute(
        select(ExerciseTopic.exercise_id, ExerciseTopic.role, ExerciseTopic.confidence)
        .where(ExerciseTopic.topic_id == topic_id)
    ).all()
    out: list[dict] = []
    for ex_id, role, conf in rows:
        ex = session.get(Exercise, ex_id)
        if ex is None:
            continue
        doc = session.get(SourceDocument, ex.source_document_id) if ex.source_document_id else None
        out.append({
            "number": ex.exercise_number,
            "source": doc.file_ref if doc else None,
            "role": (role.value if hasattr(role, "value") else str(role)),
            "confidence": round(conf, 3) if conf is not None else None,
        })
    out.sort(key=lambda r: (r["source"] or "", r["number"]))
    return out


def build_export(session: Session, topic_id: int) -> dict:
    topic = session.get(Topic, topic_id)
    if topic is None:
        raise ExportError(f"topic {topic_id} not found")
    code = topic.official_requirement_code
    if not code:
        raise ExportError(f"topic {topic_id} has no official_requirement_code")

    ke = session.scalars(
        select(KnowledgeExtraction).where(KnowledgeExtraction.topic_id == topic_id)
    ).one_or_none()
    if ke is None:
        raise ExportError(f"{code}: no extraction on record — run knowledge.run first")

    flags = list(
        session.scalars(
            select(KnowledgeFlag).where(
                KnowledgeFlag.topic_id == topic_id, KnowledgeFlag.resolved.is_(False)
            ).order_by(KnowledgeFlag.id)
        )
    )

    data: dict[str, Any] = {
        "requirement_code": code,
        "name": topic.name,
        "unit": f"{topic.unit.code} {topic.unit.name}" if topic.unit else None,
        "requirement_text": topic.statement_latex or topic.description,
        "extraction": {
            "agent": ke.agent_name,
            "model": ke.model,
            "prompt_version": ke.prompt_version,
            "exercises": ke.exercises,
            "extracted_at": ke.extracted_at.isoformat() if ke.extracted_at else None,
            "approved_at": ke.approved_at.isoformat() if ke.approved_at else None,
            "approved_by": ke.approved_by,
        },
        "concepts": [
            _item_dict(session, c, ["name", "description", "explanation", "difficulty"])
            for c in _approved(session, Concept, topic_id)
        ],
        "formulas": [
            _item_dict(session, f, ["name", "latex_raw", "description", "conditions"])
            for f in _approved(session, Formula, topic_id)
        ],
        "methods": [
            _item_dict(session, m, ["name", "when_to_use", "steps"])
            for m in _approved(session, Method, topic_id)
        ],
        "examples": [
            _item_dict(session, e, ["statement", "worked_solution", "difficulty"])
            for e in _approved(session, Example, topic_id)
        ],
        "objectives": [
            _item_dict(session, o, ["statement", "bloom_level"])
            for o in _approved(session, LearningObjective, topic_id)
        ],
        "misconceptions": [
            _item_dict(session, mc, [
                "name", "description", "incorrect_reasoning", "correct_reasoning",
                "severity", "source_kind", "distractor",
            ])
            for mc in _approved(session, Misconception, topic_id)
        ],
        "flags": [
            {"kind": fl.kind.value, "item_kind": fl.item_kind, "detail": fl.detail}
            for fl in flags
        ],
        "exercises": _exercise_index(session, topic_id),
    }
    # normalise enum values in misconceptions
    for mc in data["misconceptions"]:
        if hasattr(mc.get("source_kind"), "value"):
            mc["source_kind"] = mc["source_kind"].value
    return data


class _Dumper(yaml.SafeDumper):
    pass


def _str_representer(dumper: yaml.Dumper, value: str):
    style = "|" if "\n" in value else None
    return dumper.represent_scalar("tag:yaml.org,2002:str", value, style=style)


_Dumper.add_representer(str, _str_representer)


def dump_yaml(data: dict) -> str:
    return yaml.dump(
        data, Dumper=_Dumper, sort_keys=False, allow_unicode=True, width=100
    )


def _review_item(session: Session, topic_id: int) -> ReviewItem | None:
    return session.scalars(
        select(ReviewItem).where(
            ReviewItem.item_type == ReviewItemType.KNOWLEDGE_SPEC,
            ReviewItem.ref_table == "topics",
            ReviewItem.ref_id == topic_id,
        )
    ).one_or_none()


def export_topic(
    session: Session, topic_id: int, *, reviewer: str | None = None,
    force_unreviewed: bool = False,
) -> Path:
    topic = session.get(Topic, topic_id)
    if topic is None or not topic.official_requirement_code:
        raise ExportError(f"topic {topic_id}: no requirement code")
    code = topic.official_requirement_code

    ri = _review_item(session, topic_id)
    if not force_unreviewed:
        if ri is None:
            raise ExportError(f"{code}: no review card — nothing has been reviewed")
        if ri.status is ReviewStatus.OPEN:
            raise ExportError(f"{code}: review card is still OPEN — approve it first")
        if ri.status is ReviewStatus.REJECTED:
            raise ExportError(f"{code}: review card was REJECTED — not an approved spec")

    data = build_export(session, topic_id)
    path = export_path(code)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dump_yaml(data), encoding="utf-8")

    ke = session.scalars(
        select(KnowledgeExtraction).where(KnowledgeExtraction.topic_id == topic_id)
    ).one_or_none()
    if ke is not None:
        now = datetime.now(timezone.utc)
        ke.exported_at = now
        ke.export_path = str(path)
        if ke.approved_at is None:
            ke.approved_at = now
        if reviewer and not ke.approved_by:
            ke.approved_by = reviewer
        session.flush()
    return path


def load_export(code: str) -> dict:
    return yaml.safe_load(export_path(code).read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- #

def _main(argv: list[str]) -> int:
    force = "--force-unreviewed" in argv
    codes = [a for a in argv if not a.startswith("-")]
    do_all = "--all" in argv
    with session_scope() as s:
        if do_all:
            rows = s.execute(
                select(Topic.id, Topic.official_requirement_code).where(
                    Topic.official_requirement_code.is_not(None)
                )
            ).all()
            targets = [(tid, c) for tid, c in rows]
        else:
            if not codes:
                print("usage: python -m zaspro.knowledge.export <CODE...> | --all")
                return 2
            rows = s.execute(
                select(Topic.id, Topic.official_requirement_code).where(
                    Topic.official_requirement_code.in_(codes)
                )
            ).all()
            targets = [(tid, c) for tid, c in rows]

        wrote = skipped = failed = 0
        for tid, code in sorted(targets, key=lambda t: t[1]):
            try:
                path = export_topic(s, tid, force_unreviewed=force)
                print(f"  wrote {path}")
                wrote += 1
            except ExportError as e:
                if do_all:
                    skipped += 1
                else:
                    print(f"  SKIP {code}: {e}")
                    failed += 1
        print(f"\n{wrote} exported"
              + (f", {skipped} not ready" if do_all else "")
              + (f", {failed} failed" if failed else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
