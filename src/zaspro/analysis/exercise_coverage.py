"""Rough exercise-per-topic coverage for podstawowy.

Signal: the `zasady oceniania` cites, per task, the podstawa requirement codes
it tests ("Wymaganie szczegółowe: I.4) …"). That is CKE's own mapping — free,
and good enough to answer "how many topics have >= 5 exercises, and can this
corpus ever support the EXERCISES episode format (5 per topic)?".

Caveats (this is not the mapping agent):
* maj-2024 cites the superseded `wymagania egzaminacyjne 2024`, whose item
  numbering mostly but not exactly matches Dz.U. 2024. Codes are matched by
  string; a few 2024 rows may land on the wrong requirement.
* a task testing several requirements counts toward each.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from zaspro.db.models import Exercise, SourceDocument, Topic, TopicLevel

ROOT = Path(__file__).resolve().parents[3]
RAW = ROOT / "sources" / "raw"

# period after the (sub)task number is optional (pre-2024 multi-variant zasady)
_ZAD = re.compile(r"^Zadanie\s+(\d+(?:\.\d+)?)\.?\s*\(0", re.MULTILINE)
_CODE = re.compile(r"\b((?:XIII|XII|XI|X|IX|VIII|VII|VI|IV|V|III|II|I)\.\d+)\)")
_REQ_SECTION_END = re.compile(r"Zasady oceniania|Rozwiązanie|Przykładowe|Schemat")


def _zasady_text(session_code: str) -> str:
    import subprocess

    candidates = [
        RAW / f"MMAP-P0-660-{session_code}-zasady.pdf",
        RAW / f"MMAP-P0-100-{session_code}-zasady.pdf",
    ]
    # older sessions: one concatenated-variant PDF, e.g.
    # MMAP-P0-100-200-300-400-660-700-Q00-2209-zasady.pdf
    globbed = sorted(RAW.glob(f"MMAP-P0-*-{session_code}-zasady.pdf"))
    candidates += [g for g in globbed if "-660-" in g.name] or globbed
    for p in candidates:
        if p.is_file():
            return subprocess.run(
                ["pdftotext", "-layout", str(p), "-"],
                capture_output=True, text=True, check=True,
            ).stdout
    raise FileNotFoundError(f"no zasady for session {session_code}")


def codes_by_task(session_code: str) -> dict[str, list[str]]:
    """Task number -> podstawa codes cited in its 'Wymaganie szczegółowe' box."""

    text = _zasady_text(session_code)
    marks = list(_ZAD.finditer(text))
    out: dict[str, list[str]] = {}
    for i, m in enumerate(marks):
        start = m.end()
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        block = text[start:end]
        # the requirement box is the run before "Zasady oceniania" / "Rozwiązanie"
        cut = _REQ_SECTION_END.search(block)
        box = block[: cut.start()] if cut else block
        codes = []
        for c in _CODE.findall(box):
            if c not in codes:
                codes.append(c)
        out[m.group(1)] = codes
    return out


@dataclass
class Coverage:
    session_codes: list[str]
    podstawowy_topics: int
    # a requirement counts as "primary" for a task only if it is the FIRST code
    # the zasady cites in that task's box (CKE lists the main requirement first);
    # "touch" counts every cited code. Different questions — see
    # m3/mapping_multitopic_scan.md and SPEC settled decision 10.
    per_topic_primary: Counter
    per_topic_touch: Counter
    unmatched_codes: Counter  # code cited by zasady but not a podstawowy topic
    tasks_with_no_code: int = 0
    matched_task_code_pairs: int = 0

    def _hist(self, counts: Counter) -> dict[str, int]:
        buckets = {"0": self.podstawowy_topics - len(set(counts)), "1-2": 0, "3-4": 0, "5+": 0}
        for n in counts.values():
            buckets["1-2" if n <= 2 else "3-4" if n <= 4 else "5+"] += 1
        return buckets

    @property
    def histogram_primary(self) -> dict[str, int]:
        return self._hist(self.per_topic_primary)

    @property
    def histogram_touch(self) -> dict[str, int]:
        return self._hist(self.per_topic_touch)


def analyse(session: Session) -> Coverage:
    topic_codes = set(
        session.scalars(
            select(Topic.official_requirement_code).where(Topic.level == TopicLevel.PODSTAWOWY)
        )
    )

    # every ingested czarnodruk arkusz, both namings (…-660-A-SSSS-arkusz.docx
    # and the older …-660-SSSS.docx). A paper that fails its gate has no
    # exercises persisted, so it simply contributes nothing.
    docs = session.scalars(
        select(SourceDocument).where(SourceDocument.file_ref.like("MMAP-P0-660-%.docx"))
    ).all()

    primary: Counter = Counter()
    touch: Counter = Counter()
    unmatched: Counter = Counter()
    no_code = 0
    pairs = 0
    sessions: list[str] = []

    for doc in sorted(docs, key=lambda d: d.session_code or ""):
        sessions.append(doc.session_code)
        by_task = codes_by_task(doc.session_code)
        leaves = session.scalars(
            select(Exercise).where(
                Exercise.source_document_id == doc.id,
                Exercise.points_available.is_not(None),
            )
        ).all()
        for ex in leaves:
            codes = by_task.get(ex.exercise_number, [])
            if not codes:
                no_code += 1
                continue
            for i, code in enumerate(codes):
                pairs += 1
                if code not in topic_codes:
                    unmatched[code] += 1
                    continue
                touch[code] += 1
                if i == 0:  # first code cited = the primary requirement
                    primary[code] += 1

    return Coverage(
        session_codes=sessions,
        podstawowy_topics=len(topic_codes),
        per_topic_primary=primary,
        per_topic_touch=touch,
        unmatched_codes=unmatched,
        tasks_with_no_code=no_code,
        matched_task_code_pairs=pairs,
    )
