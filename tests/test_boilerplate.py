from pathlib import Path

import pytest

from zaspro.extraction.boilerplate import strip_boilerplate

FIX = Path(__file__).parent / "fixtures" / "mini_arkusz.tex"


def test_head_and_tail_stripped_body_kept():
    body, report = strip_boilerplate(FIX.read_text(encoding="utf-8"))

    # Body is kept from the first task marker on, so segment.py can anchor on it.
    assert body.lstrip().startswith("Zadanie 1. (0--1)")
    assert "WYPEŁNIA ZESPÓŁ NADZORUJĄCY" not in body  # cover longtable gone
    assert "Instrukcja dla zdającego" not in body  # instruction enumerate gone
    assert "Koniec" not in body
    assert "MATEMATYKA" not in body  # trailing header repeat gone

    # A longtable that belongs to a real task (Zadanie 4) must survive.
    assert body.count("\\begin{longtable}") == 1
    assert "Podaj medianę" in body

    assert report.end_sentinel_found is True
    assert report.head_environments["longtable"] == 1
    assert report.head_environments["enumerate"] == 1
    assert report.head_chars_removed > 0
    assert report.tail_chars_removed > 0


def test_missing_first_task_raises():
    with pytest.raises(ValueError):
        strip_boilerplate("no markers here at all\n\njust prose\n")
