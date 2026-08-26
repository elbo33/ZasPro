"""M0.3 study is reproducible, and the \\log_{8}{...} case is a pinned baseline.

Normalisation itself is M5. Until then this locks in the *current* (wrong)
behaviour of a naive parse so M5 has a red test to turn green (SPEC §18).

Reads the committed `m0/normalisation_sample.jsonl` (the M0.3 deliverable) so
the test is hermetic — no DOCX conversion, no `m0/_work/` needed.
"""

import json
from pathlib import Path

import sympy

from zaspro.m0.normalisation_study import FAIL_VERDICTS, _verdict_for, try_parse

SAMPLE = Path(__file__).resolve().parents[1] / "m0" / "normalisation_sample.jsonl"
LOG_CASE = r"\log_{8}{4 - \log_{8}32}"


def _rows() -> list[dict]:
    return [json.loads(line) for line in SAMPLE.read_text().splitlines() if line.strip()]


def test_sample_is_30_and_covers_every_category():
    rows = _rows()
    assert len(rows) == 30
    cats = {c for r in rows for c in r["categories"]}
    assert {"fraction", "radical", "log", "power", "system_piecewise", "text_wrap"} <= cats


def test_failure_rate_is_stable():
    rows = _rows()
    # the committed verdicts and a fresh classification must agree
    assert all(r["verdict"] == _verdict_for(r["raw"])[0] for r in rows)
    fails = sum(1 for r in rows if r["verdict"] in FAIL_VERDICTS)
    assert fails == 11  # 7 parse errors + 1 ambiguous + 2 not-checkable + 1 silent-wrong


def test_log_brace_group_case_is_silently_wrong():
    # rendered maths: log_8(4) - log_8(32) == 2/3 - 5/3 == -1
    intended = sympy.Rational(2, 3) - sympy.Rational(5, 3)
    assert intended == -1

    result = try_parse(LOG_CASE)
    assert result["parse_status"] == "OK"  # no error is raised — that is the danger

    from sympy.parsing.latex import parse_latex

    got = parse_latex(LOG_CASE, backend="lark")
    assert sympy.simplify(got - intended) != 0  # naive parse != intended

    assert _verdict_for(LOG_CASE)[0] == "WRONG_SILENT"
