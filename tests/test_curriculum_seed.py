"""Sanity checks on the committed M0.6 curriculum seed (structure, not content).

Node-by-node content verification against Dz.U. 2024 poz. 1019 is a human task
(SPEC M0.6); this only guards against accidental file corruption. Full
curriculum-tree tests come in M1.
"""

import re
from pathlib import Path

SEED = Path(__file__).resolve().parents[1] / "seeds" / "curriculum_matematyka.yaml"

ROMAN = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII", "XIII"]


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


def test_draft_status_is_flagged():
    assert "status: DRAFT" in SEED.read_text(encoding="utf-8")
