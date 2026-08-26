"""Strip arkusz cover / trailing boilerplate before segmentation (SPEC M0.2).

Pandoc has no page model, so the running header band, the invigilator answer
grid (a wide ``longtable``), the cover security notice and the closing
header/footer repeats all land inline in the LaTeX. Everything that matters
sits between the first ``Zadanie N.`` marker and the ``Koniec`` sentinel.

The strip is deliberately conservative: it removes only the head (before the
first task) and the tail (from ``Koniec`` onward). It never touches the body,
because real tasks contain their own ``longtable`` data tables (e.g. statistics
exercises) and figures.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_FIRST_TASK = re.compile(r"^Zadanie\s+\d+\.\s*(?:\(|$)", re.MULTILINE)
_END_SENTINEL = re.compile(r"^Koniec\s*$", re.MULTILINE)

_COUNT_PATTERNS = {
    "longtable": re.compile(r"\\begin\{longtable\}"),
    "includegraphics": re.compile(r"\\includegraphics"),
    "enumerate": re.compile(r"\\begin\{enumerate\}"),
}


@dataclass(frozen=True)
class StripReport:
    head_chars_removed: int
    tail_chars_removed: int
    end_sentinel_found: bool
    head_environments: dict[str, int]

    def summary(self) -> str:
        envs = ", ".join(f"{k}×{v}" for k, v in self.head_environments.items() if v)
        return (
            f"head: {self.head_chars_removed} chars removed ({envs or 'no environments'}); "
            f"tail: {self.tail_chars_removed} chars removed "
            f"(Koniec sentinel {'found' if self.end_sentinel_found else 'NOT found'})"
        )


def strip_boilerplate(latex: str) -> tuple[str, StripReport]:
    head_match = _FIRST_TASK.search(latex)
    if head_match is None:
        raise ValueError("no 'Zadanie N.' marker found — not an arkusz body?")
    head = latex[: head_match.start()]
    rest = latex[head_match.start() :]

    end_match = _END_SENTINEL.search(rest)
    if end_match is not None:
        body = rest[: end_match.start()]
        tail = rest[end_match.start() :]
    else:
        body = rest
        tail = ""

    report = StripReport(
        head_chars_removed=len(head),
        tail_chars_removed=len(tail),
        end_sentinel_found=end_match is not None,
        head_environments={
            name: len(pat.findall(head)) for name, pat in _COUNT_PATTERNS.items()
        },
    )
    return body.strip() + "\n", report
