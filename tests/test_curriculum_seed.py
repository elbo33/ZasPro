"""Sanity checks on the committed M0.6 curriculum seed (structure, not content).

Node-by-node content verification against Dz.U. 2024 poz. 1019 is a human task
(SPEC M0.6); this only guards against accidental file corruption. Full
curriculum-tree tests come in M1.
"""

import re
from pathlib import Path

from zaspro.m0.curriculum_seed import FORMULA_ROWS

SEED = Path(__file__).resolve().parents[1] / "seeds" / "curriculum_matematyka.yaml"

ROMAN = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII", "XIII"]
MAS = range(0x1D400, 0x1D800)


def _codes() -> list[str]:
    return re.findall(r"^\s+- code: (\S+)", SEED.read_text(encoding="utf-8"), re.MULTILINE)


def test_thirteen_units_in_order():
    units = re.findall(r"^  - code: (\S+)", SEED.read_text(encoding="utf-8"), re.MULTILINE)
    assert units == ROMAN


def test_topic_counts_match_the_regulation():
    text = SEED.read_text(encoding="utf-8")
    assert text.count("level: podstawowy") == 73
    assert text.count("level: rozszerzony") == 46


def test_every_code_is_unique():
    codes = _codes()
    assert len(codes) == len(set(codes))


def test_codes_are_well_formed():
    for c in _codes():
        assert re.fullmatch(r"(I|II|III|IV|V|VI|VII|VIII|IX|X|XI|XII|XIII)(\.(R?\d+))?", c), c


def test_status_is_verified_and_attributed():
    text = SEED.read_text(encoding="utf-8")
    assert "status: VERIFIED" in text
    assert re.search(r"verified_by: \S", text)
    assert re.search(r"verified_on: \d{4}-\d{2}-\d{2}", text)


def test_no_doubled_math_alphanumeric_survived_into_the_seed():
    text = SEED.read_text(encoding="utf-8")
    assert not any(ord(ch) in MAS for ch in text), "corrupted math chars in seed"


def test_every_formula_row_has_statement_latex():
    text = SEED.read_text(encoding="utf-8")
    for code in FORMULA_ROWS:
        # the code line is followed by level then name then statement_latex
        block = text.split(f"- code: {code}\n", 1)[1].split("- code:", 1)[0]
        assert "statement_latex:" in block, f"{code} missing statement_latex"


def test_formula_row_names_are_plain_prose():
    # Inline notation like "y = f(x)" may stay in the name as plain text
    # (the user's instruction); LaTeX and corrupted math chars may not.
    for code, fx in FORMULA_ROWS.items():
        name = fx["name"]
        assert not any(ord(c) in MAS for c in name), f"{code} name has corrupted math chars"
        assert "\\" not in name, f"{code} name contains LaTeX"
        assert "statement_latex" in fx and fx["statement_latex"]
