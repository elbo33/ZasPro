"""Write m2/exercise_coverage.md.

    uv run python -m zaspro.analysis.coverage_run
"""

from __future__ import annotations

import sys

from sqlalchemy import select

from zaspro.analysis.exercise_coverage import ROOT, analyse
from zaspro.db.base import session_scope
from zaspro.db.models import Topic, TopicLevel

OUT = ROOT / "m2" / "exercise_coverage.md"

_ROMAN = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII", "XIII"]


def _code_key(code: str) -> tuple[int, int]:
    unit, _, item = code.partition(".")
    return (_ROMAN.index(unit) if unit in _ROMAN else 99, int(item) if item.isdigit() else 0)


def main() -> int:
    with session_scope() as s:
        cov = analyse(s)
        names = dict(
            s.execute(
                select(Topic.official_requirement_code, Topic.name).where(
                    Topic.level == TopicLevel.PODSTAWOWY
                )
            ).all()
        )

    hp = cov.histogram_primary
    ht = cov.histogram_touch
    n_topics = cov.podstawowy_topics
    n_sessions = len(cov.session_codes)

    zeros = sorted((c for c in names if c not in cov.per_topic_primary), key=_code_key)
    five_plus = sorted(
        (c for c in cov.per_topic_primary if cov.per_topic_primary[c] >= 5),
        key=lambda c: -cov.per_topic_primary[c],
    )

    L = [
        "# Rough exercise coverage — podstawowy",
        "",
        "**Signal:** the `zasady oceniania` cites the podstawa requirement codes "
        "each task tests. This is CKE's own mapping, parsed cheaply — **not** the "
        "M3 mapping agent. maj-2024 cites the superseded *wymagania egzaminacyjne "
        "2024* (numbering mostly matches Dz.U. 2024; a few rows may be off).",
        "",
        f"Corpus: sessions {', '.join(cov.session_codes)} "
        f"({cov.matched_task_code_pairs} task→code citations, "
        f"{cov.tasks_with_no_code} leaf tasks with no parseable code).",
        "",
        "## Two counts, deliberately",
        "",
        "**primary** = the task's first-cited requirement (the one it mainly "
        "drills). **touches** = any requirement the task cites. A task that "
        "builds a system of equations *and* interprets a linear coefficient is "
        "one primary + one touch. The EXERCISES episode format wants five that "
        "**primarily** drill a requirement; touches are supporting material. Do "
        "not read the touches column as progress the primary column doesn't "
        "show (SPEC settled decision 10; `m3/mapping_multitopic_scan.md`).",
        "",
        f"| exercises per requirement | primarily drills | also touches |",
        "|---|---|---|",
        f"| 0 | {hp['0']} | {ht['0']} |",
        f"| 1–2 | {hp['1-2']} | {ht['1-2']} |",
        f"| 3–4 | {hp['3-4']} | {ht['3-4']} |",
        f"| 5+ | {hp['5+']} | {ht['5+']} |",
        "",
        f"Covered as **primary** (≥1): **{n_topics - hp['0']} / {n_topics}**. "
        f"At the EXERCISES 5-per-topic bar, **primary**: **{hp['5+']} / {n_topics}** "
        f"(touches: {ht['5+']}).",
        "",
        "## Requirements with 5+ exercises that primarily drill them",
        "",
    ]
    if five_plus:
        for c in five_plus:
            L.append(
                f"- `{c}` ×{cov.per_topic_primary[c]} primary "
                f"(+{cov.per_topic_touch[c] - cov.per_topic_primary[c]} touch) — {names[c]}"
            )
    else:
        L.append("_none._")

    L += [
        "",
        f"## Requirements with zero primary exercises ({len(zeros)})",
        "",
        ", ".join(f"`{c}`" for c in zeros) or "_none._",
        "",
    ]
    if cov.unmatched_codes:
        L += [
            "## Codes cited by a zasady but not a podstawowy topic",
            "",
            ", ".join(f"`{c}`×{n}" for c, n in cov.unmatched_codes.most_common()),
            "",
            "(rozszerzony codes, or maj-2024 numbering that diverged from Dz.U. 2024)",
            "",
        ]

    L += [
        "## Read",
        "",
        f"{n_sessions} ingested papers give a **primary** exercise for "
        f"{n_topics - hp['0']} of {n_topics} requirements; the EXERCISES "
        f"five-per-topic bar is met (primary) for {hp['5+']}. Counting touches "
        f"as well moves that to {ht['5+']}, but a touch is not what the format "
        f"needs. {hp['0'] + hp['1-2']} requirements still have two or fewer "
        "exercises that primarily drill them, and CKE publishes ~2 podstawowy "
        "sessions a year. Reading it straight (SPEC settled decision 10): the "
        "deterministic corpus is calibration and seed material, not supply. The "
        "Exercise Agent (M5, generation + symbolic verification) is load-bearing "
        "for the EXERCISES format. Harvested arkusze anchor difficulty and "
        "Matura-authentic phrasing; generated-and-verified exercises are the "
        "majority for most topics.",
        "",
    ]
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text("\n".join(L), encoding="utf-8")

    print(f"primary  histogram: {hp}")
    print(f"touches  histogram: {ht}")
    print(f"covered (primary) {n_topics - hp['0']}/{n_topics}, 5+ primary: {hp['5+']}, 5+ touch: {ht['5+']}")
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
