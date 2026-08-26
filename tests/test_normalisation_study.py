"""M0.3 study is reproducible, and the \\log_{8}{...} case is a pinned baseline.

Normalisation itself is M5. Until then this locks in the *current* (wrong)
behaviour of a naive parse so M5 has a red test to turn green (SPEC §18).
"""

import sympy

from zaspro.m0.normalisation_study import (
    FAIL_VERDICTS,
    build_sample,
    extract,
    _verdict_for,
    try_parse,
)

LOG_CASE = r"\log_{8}{4 - \log_{8}32}"


def test_sample_is_30_and_covers_every_category():
    sample = build_sample(extract())
    assert len(sample) == 30
    cats = {c for r in sample for c in r["categories"]}
    assert {"fraction", "radical", "log", "power", "system_piecewise", "text_wrap"} <= cats


def test_failure_rate_is_stable():
    sample = build_sample(extract())
    fails = sum(1 for r in sample if _verdict_for(r["raw"])[0] in FAIL_VERDICTS)
    assert fails == 11  # 7 parse errors + 1 ambiguous + 2 not-checkable + 1 silent-wrong
    assert all(_verdict_for(r["raw"])[0] != "UNREVIEWED" for r in sample)


def test_log_brace_group_case_is_silently_wrong():
    # rendered maths: log_8(4) - log_8(32) == 2/3 - 5/3 == -1
    intended = sympy.Rational(2, 3) - sympy.Rational(5, 3)
    assert intended == -1

    result = try_parse(LOG_CASE)
    assert result["parse_status"] == "OK"  # no error is raised — that is the danger

    from sympy.parsing.latex import parse_latex

    got = parse_latex(LOG_CASE, backend="lark")
    assert sympy.simplify(got - intended) != 0  # naive parse != intended

    assert _verdict_for(LOG_CASE) == (
        "WRONG_SILENT",
        _verdict_for(LOG_CASE)[1],
    )
