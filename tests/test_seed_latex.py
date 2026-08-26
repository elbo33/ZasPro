"""Every `statement_latex` in the curriculum seed must be valid LaTeX.

A syntax error in the curriculum notation reference would propagate into every
episode built from that topic and only surface as a rendering failure in a
renderer that does not exist yet. So compile them here.

Needs a TeX install (`pdflatex`). Skips cleanly without one; run it on a
machine that has TeX (and any CI image that ships one) to get the guarantee.
"""

import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

from zaspro.m0.curriculum_seed import FORMULA_ROWS

SEED = Path(__file__).resolve().parents[1] / "seeds" / "curriculum_matematyka.yaml"
PDFLATEX = shutil.which("pdflatex")

# The preamble a renderer must provide (m0/curriculum_notes.md): \tg and \ctg
# are not standard LaTeX.
PREAMBLE = r"""\documentclass{article}
\usepackage{amsmath}
\DeclareMathOperator{\tg}{tg}
\DeclareMathOperator{\ctg}{ctg}
\begin{document}
"""


def _seed_latex_values() -> list[str]:
    """The statement_latex values as committed in the seed YAML (unescaped)."""

    out = []
    for m in re.finditer(r'^\s*statement_latex:\s*"(.*)"\s*$', SEED.read_text("utf-8"), re.M):
        out.append(m.group(1).replace('\\"', '"').replace("\\\\", "\\"))
    return out


def test_seed_holds_all_20_transcriptions():
    values = _seed_latex_values()
    assert len(values) == 20
    assert set(values) == {fx["statement_latex"] for fx in FORMULA_ROWS.values()}


def _compile(fragments: list[str]) -> subprocess.CompletedProcess:
    body = "\n".join(rf"\[ {v} \]" for v in fragments)
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / "seed.tex").write_text(PREAMBLE + body + "\n\\end{document}\n", "utf-8")
        return subprocess.run(
            [PDFLATEX, "-halt-on-error", "-interaction=nonstopmode", "seed.tex"],
            cwd=d,
            capture_output=True,
            text=True,
            timeout=120,
        )


@pytest.mark.skipif(PDFLATEX is None, reason="pdflatex not installed")
def test_every_statement_latex_compiles():
    values = _seed_latex_values()
    result = _compile(values)
    if result.returncode == 0:
        return

    # one of them is broken — recompile individually to name it
    broken = []
    for fx_code, fx in FORMULA_ROWS.items():
        if _compile([fx["statement_latex"]]).returncode != 0:
            broken.append(fx_code)
    pytest.fail(
        f"statement_latex failed to compile: {broken or '(combined only)'}\n"
        + result.stdout[-2000:]
    )
