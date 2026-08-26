"""M0.3 — characterise pandoc LaTeX vs a naive parse.

SPEC M0.3: sample 30 equations across fractions, radicals, logs, powers,
systems and piecewise; for each, record whether the pandoc LaTeX parses to the
intended expression; report the failure rate and the failure patterns. This
does NOT build the normalisation layer (that is M5) — it produces the number
M5 is scoped from, and stores raw + normalised(=None) from the start.

Run:  uv run python -m zaspro.m0.normalisation_study
Writes m0/normalisation_study.md and m0/normalisation_sample.jsonl.
The verdict column in the .md is filled in by hand; this script produces the
raw parse outcomes it is based on.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from sympy.parsing.latex import parse_latex

ROOT = Path(__file__).resolve().parents[3]
WORK = ROOT / "m0" / "_work"
OUT = ROOT / "m0"

TEX_FILES = [
    WORK / "MMAP-P0-660-A-2605-arkusz" / "MMAP-P0-660-A-2605-arkusz.tex",
    WORK / "Informator_EM2024_matematyka_pp_660" / "Informator_EM2024_matematyka_pp_660.tex",
]

_INLINE = re.compile(r"\\\((.+?)\\\)", re.DOTALL)
_DISPLAY = re.compile(r"\\\[(.+?)\\\]", re.DOTALL)

# The three cases SPEC / the spike call out explicitly; always in the sample.
PINNED = [
    r"\log_{8}{4 - \log_{8}32}",
    r"\sqrt{\frac{25}{\text{8}}} \cdot \sqrt{2} + 2^{- 1}",
    r"f(x) = \left\{ \ \begin{matrix}\nx + 2 & \text{dla}\text{ }x \in \lbrack - 4,\ 2\rbrack \\\n - x + 5 & \text{dla}\text{ }x \in (2,\ 4\rbrack\n\end{matrix} \right.\ ",
]

CATEGORIES = ("fraction", "radical", "log", "power", "system_piecewise", "text_wrap")
# how many of each to include (pinned cases count toward their categories)
QUOTA = {"fraction": 5, "radical": 5, "log": 6, "power": 5, "system_piecewise": 5, "text_wrap": 4}


def categorise(s: str) -> set[str]:
    f: set[str] = set()
    if r"\frac" in s:
        f.add("fraction")
    if r"\sqrt" in s:
        f.add("radical")
    if r"\log" in s or r"\ln" in s or r"\lg" in s:
        f.add("log")
    if re.search(r"\^\s*[{\-\d(]", s):
        f.add("power")
    if any(t in s for t in (r"\begin{matrix}", r"\begin{cases}", r"\left\{", r"\\\\")):
        f.add("system_piecewise")
    if r"\text{" in s:
        f.add("text_wrap")
    return f


def extract() -> list[dict]:
    seen: set[str] = set()
    out: list[dict] = []
    for tex in TEX_FILES:
        txt = tex.read_text(encoding="utf-8")
        for pat, kind in ((_INLINE, "inline"), (_DISPLAY, "display")):
            for m in pat.finditer(txt):
                raw = m.group(1).strip()
                if raw in seen:
                    continue
                seen.add(raw)
                cats = categorise(raw)
                if cats:
                    out.append({"source": tex.stem, "kind": kind, "raw": raw, "categories": sorted(cats)})
    return out


def try_parse(raw: str) -> dict:
    try:
        expr = parse_latex(raw, backend="lark")
        return {"parse_status": "OK", "parsed": str(expr)}
    except Exception as exc:  # lark raises many types; all are "did not parse"
        return {"parse_status": "PARSE_ERROR", "parsed": f"{type(exc).__name__}: {str(exc).splitlines()[0][:120]}"}


def build_sample(pool: list[dict]) -> list[dict]:
    chosen: list[dict] = []
    chosen_raw: set[str] = set()

    for raw in PINNED:
        rec = next((r for r in pool if r["raw"] == raw), None)
        if rec is None:
            rec = {"source": "spec/spike", "kind": "pinned", "raw": raw, "categories": sorted(categorise(raw))}
        chosen.append(rec)
        chosen_raw.add(raw)

    filled = {c: sum(1 for r in chosen if c in r["categories"]) for c in CATEGORIES}
    for cat in CATEGORIES:
        for rec in pool:
            if len(chosen) >= 30:
                break
            if filled[cat] >= QUOTA[cat]:
                break
            if rec["raw"] in chosen_raw or cat not in rec["categories"]:
                continue
            chosen.append(rec)
            chosen_raw.add(rec["raw"])
            for c in rec["categories"]:
                if c in filled:
                    filled[c] += 1

    # top up to exactly 30 with any remaining structured equations, document order
    for rec in pool:
        if len(chosen) >= 30:
            break
        if rec["raw"] not in chosen_raw:
            chosen.append(rec)
            chosen_raw.add(rec["raw"])

    return chosen[:30]


# Verdict per sampled equation, keyed by raw LaTeX. Assigned by inspection of
# the pandoc output against the rendered intent (M0.3 is analytical, not solved).
#   OK                    naive parse yields the intended expression
#   WRONG_SILENT          parses successfully to a DIFFERENT expression
#   AMBIGUOUS             parser returns an ambiguity it cannot resolve
#   PARSE_ERROR           does not parse at all
#   NOT_MACHINE_CHECKABLE notation that is not an expression (sets, |AB| lengths)
VERDICTS: dict[str, tuple[str, str]] = {
    r"\log_{8}{4 - \log_{8}32}": ("WRONG_SILENT", "brace group after \\log_b swallowed as the argument: log_8(4 - log_8 32) instead of log_8 4 - log_8 32"),
    r"\sqrt{\frac{25}{\text{8}}} \cdot \sqrt{2} + 2^{- 1}": ("PARSE_ERROR", "digit wrapped in \\text{8} (Word run styling)"),
    "PINNED_PIECEWISE": ("PARSE_ERROR", "piecewise as \\left\\{ + \\begin{matrix}; also NOT_MACHINE_CHECKABLE as a single expression"),
    r"5^{\begin{matrix}  \frac{1}{4} \\  \   \end{matrix}}": ("PARSE_ERROR", "exponent rendered as a 1-cell matrix; intended 5**(1/4)"),
    r"5^{\begin{matrix}  \frac{1}{2} \\  \   \end{matrix}}": ("PARSE_ERROR", "exponent as matrix; intended 5**(1/2)"),
    r"5^{\begin{matrix}  \frac{3}{4} \\  \   \end{matrix}}": ("PARSE_ERROR", "exponent as matrix; intended 5**(3/4)"),
    r"\frac{1}{3}": ("OK", ""),
    r"\sqrt{5\sqrt{5}}": ("OK", "nested radical -> 5**(3/4)"),
    r"x = \sqrt{2} - 5": ("OK", ""),
    r"\sqrt{2}": ("OK", ""),
    r"2 - 20\sqrt{2}": ("OK", ""),
    r"\log{K(t)}": ("AMBIGUOUS", "K(t): function application vs multiplication; parser returns _ambig"),
    r"a = \log_{2}\left( 3\sqrt{5} + \sqrt{13} \right)": ("OK", "parenthesised \\left(...\\right) argument parses correctly — contrast the brace case"),
    r"b = \log_{2}\left( 3\sqrt{5} - \sqrt{13} \right)": ("OK", ""),
    r"\log_{2}45": ("OK", ""),
    r"\log_{2}30": ("OK", "auto-simplified to 1 + log_2 15; value-equal"),
    r"4^{12} \cdot 5^{24}": ("OK", "eagerly evaluated to 10**24; value-equal"),
    r"X = \left\{ 1,\ 3,\ 5,\ 7,\ 9 \right\}": ("NOT_MACHINE_CHECKABLE", "set literal via \\left\\{; parser errors on \\left"),
    "DISPLAY_PIECEWISE": ("PARSE_ERROR", "piecewise as \\left\\{ + \\begin{matrix}"),
    r"\frac{\text{a+}\sqrt{\text{b}}}{\text{c}}": ("PARSE_ERROR", "variables a,b,c wrapped in \\text{}; also '+' inside \\text"),
    r"x^{2} + 10x + 25": ("OK", ""),
    r"62 - 10\sqrt{2}": ("OK", ""),
    r"7n^{2} + 21n": ("OK", ""),
    r"\frac{8}{11}": ("OK", ""),
    r"|BC| = 2\sqrt{10}": ("NOT_MACHINE_CHECKABLE", "|BC| is segment length; parsed as Abs(B*C)"),
    r"\frac{1}{\sqrt{10}}": ("OK", "rationalised to sqrt(10)/10; value-equal"),
    r"\frac{3}{\sqrt{10}}": ("OK", "value-equal"),
    r"\frac{\sqrt{10}}{\sqrt{11}}": ("OK", "value-equal"),
    r"\frac{a}{b}": ("OK", ""),
    r"9\sqrt{3}": ("OK", ""),
}

FAIL_VERDICTS = {"WRONG_SILENT", "AMBIGUOUS", "PARSE_ERROR", "NOT_MACHINE_CHECKABLE"}

_NORM_VERDICTS = {re.sub(r"\s+", " ", k).strip(): v for k, v in VERDICTS.items()}


def _verdict_for(raw: str) -> tuple[str, str]:
    key = re.sub(r"\s+", " ", raw).strip()
    if key in _NORM_VERDICTS:
        return _NORM_VERDICTS[key]
    if re.match(r"^[0-9A-Za-z]+\^\{\\begin\{matrix\}", key):
        return ("PARSE_ERROR", "exponent rendered as a 1-cell matrix; intended base**(fraction)")
    if key.startswith("f(x) = \\left\\{"):
        return VERDICTS["PINNED_PIECEWISE"]
    return ("UNREVIEWED", "")


def write_md(sample: list[dict]) -> Path:
    n = len(sample)
    tally: dict[str, int] = {}
    for r in sample:
        tally[r["verdict"]] = tally.get(r["verdict"], 0) + 1
    fails = sum(v for k, v in tally.items() if k in FAIL_VERDICTS)

    L = [
        "# M0.3 — LaTeX normalisation study",
        "",
        "SPEC M0.3: characterise the problem, do not solve it. The normalisation "
        "layer is M5; this fixes the number M5 is scoped from.",
        "",
        f"**Sample:** {n} equations drawn deterministically from "
        f"{sample[0]['pool_size']} structured equations across the two Track A "
        "DOCX conversions, stratified over fractions, radicals, logs, powers, "
        "systems/piecewise and `\\text{}`-wrapped forms. The three cases SPEC and "
        "the spike call out are pinned in.",
        "",
        '**Naive parse:** `sympy.parsing.latex.parse_latex(raw, backend="lark")`, '
        "i.e. the raw pandoc LaTeX fed straight to a parser with no normalisation.",
        "",
        "## Headline",
        "",
        f"**{fails}/{n} = {fails / n:.0%} of sampled equations do not yield the "
        "intended expression from a naive parse.**",
        "",
        "| outcome | count | meaning |",
        "|---|---|---|",
        f"| OK | {tally.get('OK', 0)} | parses to the intended expression (rationalisation / eager eval is value-equal) |",
        f"| PARSE_ERROR | {tally.get('PARSE_ERROR', 0)} | does not parse — loud failure, routes to review |",
        f"| AMBIGUOUS | {tally.get('AMBIGUOUS', 0)} | parser returns an unresolved ambiguity |",
        f"| NOT_MACHINE_CHECKABLE | {tally.get('NOT_MACHINE_CHECKABLE', 0)} | notation, not an expression (sets, segment lengths) |",
        f"| WRONG_SILENT | {tally.get('WRONG_SILENT', 0)} | parses successfully to a **different** expression — the dangerous class |",
        "",
        "The single silent-wrong case is `\\log_{8}{4 - \\log_{8}32}` (SPEC §2a). "
        "It parses without error to `log_8(4 - log_8 32)` when the rendered maths "
        "is `log_8 4 - log_8 32`. This is the M5 regression fixture.",
        "",
        "## The 30 equations",
        "",
        "| # | categories | raw pandoc LaTeX | naive parse | verdict | pattern |",
        "|---|---|---|---|---|---|",
    ]
    for i, r in enumerate(sample, 1):
        raw = re.sub(r"\s+", " ", r["raw"]).replace("|", "\\|")
        parsed = re.sub(r"\s+", " ", r["parsed"]).replace("|", "\\|")
        L.append(
            f"| {i} | {'+'.join(r['categories'])} | `{raw[:120]}` | "
            f"`{parsed[:90]}` | {r['verdict']} | {r['pattern']} |"
        )

    L += [
        "",
        "## Failure patterns (what M5 normalisation must handle)",
        "",
        "1. **`\\text{}` wrapping of operands/operators.** Word run styling makes "
        "pandoc emit `\\text{8}`, `\\text{a+}`, `\\text{dla}`. The parser rejects "
        "the backslash. 48 of 401 structured equations carry `\\text{}`. "
        "Normalisation: strip `\\text{}` around mathematical content, keep it "
        "around genuine prose.",
        "2. **Piecewise / sets as `\\left\\{` + `\\begin{matrix}`.** `f(x) = "
        "\\left\\{ \\begin{matrix} … \\end{matrix} \\right.` and `X = \\left\\{ 1, "
        "3, 5 \\right\\}`. Not expressions. Map to `Piecewise` / `FiniteSet`, or "
        "mark `NOT_MACHINE_CHECKABLE`.",
        "3. **Exponent rendered as a matrix.** `5^{\\begin{matrix} \\frac{1}{4} "
        "\\\\ \\end{matrix}}` for `5**(1/4)`. Recoverable: collapse a 1-cell "
        "matrix in an exponent to its content.",
        "4. **Brace group after `\\log_b`.** `\\log_{8}{X}` binds `{X}` as the "
        "whole argument, absorbing following terms. Parenthesised arguments "
        "(`\\left( … \\right)`, rows 13–14) are fine. Normalisation must treat "
        "`\\log_{b}{…}` grouping explicitly. **Silent — this is the one that "
        "matters.**",
        "5. **Juxtaposition: function application vs multiplication.** `\\log{K(t)}`, "
        "any `f(x)`. `parse_latex` returns an `_ambig` tree. Route to review; do "
        "not guess.",
        "6. **Geometry / measure notation.** `|BC|` (segment length), vector bars. "
        "Parsed as `Abs(B*C)`. `NOT_MACHINE_CHECKABLE`.",
        "",
        "## Storage",
        "",
        "`m0/normalisation_sample.jsonl` stores each equation with `latex_raw` "
        "(pandoc, for display) and `latex_normalised: null` (M5). A row with raw "
        "and no normalised form is valid — it simply cannot be auto-verified "
        "(SPEC §5).",
        "",
    ]
    path = OUT / "normalisation_study.md"
    path.write_text("\n".join(L), encoding="utf-8")
    return path


def run() -> int:
    pool = extract()
    sample = build_sample(pool)
    for rec in sample:
        rec.update(try_parse(rec["raw"]))
        verdict, pattern = _verdict_for(rec["raw"])
        rec["verdict"] = verdict
        rec["pattern"] = pattern
        rec["pool_size"] = len(pool)
        rec["latex_raw"] = rec["raw"]
        rec["latex_normalised"] = None  # M5 fills this; stored from the start

    unreviewed = [r["raw"] for r in sample if r["verdict"] == "UNREVIEWED"]
    if unreviewed:
        print("WARNING: unreviewed equations in sample (add to VERDICTS):")
        for u in unreviewed:
            print("   ", repr(u))

    (OUT / "normalisation_sample.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in sample) + "\n", encoding="utf-8"
    )
    md = write_md(sample)

    n = len(sample)
    fails = sum(1 for r in sample if r["verdict"] in FAIL_VERDICTS)
    tally: dict[str, int] = {}
    for r in sample:
        tally[r["verdict"]] = tally.get(r["verdict"], 0) + 1
    print(f"M0.3  {n} equations from {len(pool)} structured candidates")
    print(f"      naive-parse failure rate: {fails}/{n} = {fails / n:.0%}")
    print("      " + ", ".join(f"{k} {v}" for k, v in sorted(tally.items())))
    print(f"      wrote {md.relative_to(ROOT)} and m0/normalisation_sample.jsonl")
    return 1 if unreviewed else 0


if __name__ == "__main__":
    raise SystemExit(run())
