import pytest

from zaspro.extraction.marking_scheme import parse_marking_scheme_text

SAMPLE = """\
Zasady oceniania rozwiązań zadań

Zadanie 1. (0–1)
Wymaganie ogólne ... Wymaganie szczegółowe ...
Poprawna odpowiedź: B

Zadanie 2. (0–2)
Za rozwiązanie pełne 2 punkty.

Zadanie 3.1. (0–1)
Zadanie 3.2. (0–3)

Uwaga: dotyczy zdających z dyskalkulią (punkty 1.–12.).
Zdający może otrzymać co najwyżej (n − 1) punktów.
"""


def test_parses_tasks_and_ignores_prose_false_positives():
    tasks = {t.exercise_number: t.points_available for t in parse_marking_scheme_text(SAMPLE)}
    assert tasks == {"1": 1, "2": 2, "3.1": 1, "3.2": 3}


def test_conflicting_point_values_raise():
    text = "Zadanie 7. (0–2)\n...\nZadanie 7. (0–3)\n"
    with pytest.raises(ValueError, match="two point values"):
        parse_marking_scheme_text(text)


def test_empty_raises():
    with pytest.raises(ValueError, match="no 'Zadanie"):
        parse_marking_scheme_text("nothing to see")
