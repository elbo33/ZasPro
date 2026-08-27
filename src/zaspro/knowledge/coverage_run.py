"""Rebuild `exercise_topics` and write m4/topic_chunk_coverage.md.

    uv run python -m zaspro.knowledge.coverage_run

Run before knowledge extraction. Shows the per-topic exercise count under both
definitions — *primarily drills* vs *also touches* — so the aggregation set is
visible before any API call (SPEC §11).
"""

from __future__ import annotations

import sys
from pathlib import Path

from zaspro.db.base import session_scope
from zaspro.knowledge.aggregate import rebuild_exercise_topics, topic_chunk_counts

OUT = Path(__file__).resolve().parents[3] / "m4" / "topic_chunk_coverage.md"

_ROMAN = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII", "XIII"]


def _key(code: str | None) -> tuple[int, int]:
    if not code:
        return (99, 0)
    u, _, i = code.partition(".")
    return (_ROMAN.index(u) if u in _ROMAN else 98, int(i) if i.isdigit() else 0)


def _hist(counts: list[int], total: int) -> dict[str, int]:
    b = {"0": total - sum(1 for c in counts if c), "1-2": 0, "3-4": 0, "5+": 0}
    for c in counts:
        if c == 0:
            continue
        b["1-2" if c <= 2 else "3-4" if c <= 4 else "5+"] += 1
    return b


def main() -> int:
    with session_scope() as s:
        res = rebuild_exercise_topics(s)
        rows = sorted(topic_chunk_counts(s), key=lambda r: _key(r.code))

    n = len(rows)
    prim_h = _hist([r.primary for r in rows], n)
    touch_h = _hist([r.touch for r in rows], n)

    L = [
        "# exercise_topics — per-requirement exercise coverage (M4 input)",
        "",
        "Built by `zaspro.knowledge.aggregate.rebuild_exercise_topics` from the "
        "reviewed `chunk_mappings`. **primary** = the exercise's primary "
        "requirement; **touch** = primary or approved secondary. Knowledge "
        "extraction aggregates over *touch*; the histogram is here so the set is "
        "visible before extraction (SPEC §11).",
        "",
        f"Materialised: {res.exercises_with_topics} exercises with topics "
        f"({res.primary_rows} primary + {res.secondary_rows} secondary rows). "
        f"Skipped: {res.skipped_unsettled} with an unsettled primary mapping "
        f"(rejected / still in review), {res.skipped_no_mapping} with no mapping.",
        "",
        "## Histogram over the 73 podstawowy requirements",
        "",
        "| exercises per requirement | primary | touch |",
        "|---|---|---|",
        f"| 0 | {prim_h['0']} | {touch_h['0']} |",
        f"| 1-2 | {prim_h['1-2']} | {touch_h['1-2']} |",
        f"| 3-4 | {prim_h['3-4']} | {touch_h['3-4']} |",
        f"| 5+ | {prim_h['5+']} | {touch_h['5+']} |",
        "",
        f"Covered (primary >= 1): **{n - prim_h['0']} / {n}**.  "
        f"Covered (touch >= 1): **{n - touch_h['0']} / {n}**.",
        "",
        "## Per requirement",
        "",
        "| code | primary | touch | requirement |",
        "|---|---|---|---|",
    ]
    for r in rows:
        L.append(f"| `{r.code}` | {r.primary} | {r.touch} | {r.name} |")
    L.append("")

    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text("\n".join(L), encoding="utf-8")
    print(f"exercises with topics : {res.exercises_with_topics}")
    print(f"primary rows          : {res.primary_rows}")
    print(f"secondary rows        : {res.secondary_rows}")
    print(f"skipped (unsettled)   : {res.skipped_unsettled}")
    print(f"primary  histogram    : {prim_h}")
    print(f"touch    histogram    : {touch_h}")
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
