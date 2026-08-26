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

    h = cov.histogram
    zeros = sorted((c for c in names if c not in cov.per_topic), key=_code_key)
    five_plus = sorted(
        (c for c, n in cov.per_topic.items() if n >= 5),
        key=lambda c: -cov.per_topic[c],
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
        "## Histogram over the 73 podstawowy requirements",
        "",
        "| exercises per requirement | requirements |",
        "|---|---|",
        f"| 0 | {h['0']} |",
        f"| 1–2 | {h['1-2']} |",
        f"| 3–4 | {h['3-4']} |",
        f"| 5+ | {h['5+']} |",
        "",
        f"Covered (≥1): **{cov.podstawowy_topics - h['0']} / {cov.podstawowy_topics}**. "
        f"At the EXERCISES format's 5-per-topic bar: **{h['5+']} / {cov.podstawowy_topics}**.",
        "",
        "## Requirements with 5+ exercises",
        "",
    ]
    if five_plus:
        for c in five_plus:
            L.append(f"- `{c}` ×{cov.per_topic[c]} — {names[c]}")
    else:
        L.append("_none._")

    L += [
        "",
        f"## Requirements with zero exercises ({len(zeros)})",
        "",
        ", ".join(f"`{c}`" for c in zeros),
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
        "Three papers give roughly one to two exercises for the requirements they "
        "touch and nothing for the rest. The EXERCISES episode format needs five "
        "approved exercises per topic; on this corpus that bar is met for "
        f"{h['5+']} of 73 requirements. Supporting the format as specified across "
        "podstawowy needs many more sessions harvested (order of 10–15 more "
        "arkusze, plus generated exercises to fill the long tail).",
        "",
    ]
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text("\n".join(L), encoding="utf-8")

    print(f"histogram: {h}")
    print(f"covered {cov.podstawowy_topics - h['0']}/{cov.podstawowy_topics}, 5+: {h['5+']}")
    print(f"unmatched codes: {dict(cov.unmatched_codes)}")
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
