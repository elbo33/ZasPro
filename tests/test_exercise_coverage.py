"""Rough coverage analysis: the zasady code parser, and the histogram shape."""

from zaspro.analysis import exercise_coverage as ec


def test_codes_by_task_parses_the_requirement_box(monkeypatch):
    text = (
        "Zadanie 1. (0–1)\n"
        "Wymaganie ogólne            Wymaganie szczegółowe\n"
        "I. Sprawność rachunkowa.    Zdający:\n"
        "                            I.1) wykonuje działania ...;\n"
        "                            I.4) stosuje prawa działań na pierwiastkach.\n"
        "Zasady oceniania\n"
        "1 pkt – odpowiedź poprawna.\n"
        "Rozwiązanie\n"
        "Wersja A   Wersja B\n"
        "C          B\n"
        "Zadanie 2. (0–2)\n"
        "                            VIII.10) wskazuje podstawowe punkty szczególne;\n"
        "Zasady oceniania\n"
        "2 pkt – ...\n"
        "Zadanie 3.1. (0–1)\n"
        "                            IX.3) oblicza odległość dwóch punktów.\n"
        "Rozwiązanie\n"
    )
    monkeypatch.setattr(ec, "_zasady_text", lambda _s: text)

    got = ec.codes_by_task("9999")
    assert got == {"1": ["I.1", "I.4"], "2": ["VIII.10"], "3.1": ["IX.3"]}


def test_codes_after_the_solution_block_are_not_captured(monkeypatch):
    # a code appearing in a worked solution must not count as a requirement
    text = (
        "Zadanie 1. (0–1)\n"
        "   I.7) stosuje wartość bezwzględną.\n"
        "Zasady oceniania\n"
        "Rozwiązanie\n"
        "   z twierdzenia VIII.5) wynika, że ...\n"
        "Zadanie 2. (0–1)\n"
        "   II.1) stosuje wzory skróconego mnożenia.\n"
        "Rozwiązanie\n"
    )
    monkeypatch.setattr(ec, "_zasady_text", lambda _s: text)
    got = ec.codes_by_task("9999")
    assert got["1"] == ["I.7"]  # VIII.5 in the solution is ignored
    assert got["2"] == ["II.1"]


def test_histogram_buckets_and_zero_count():
    from collections import Counter

    cov = ec.Coverage(
        session_codes=["x"],
        podstawowy_topics=10,
        per_topic=Counter({"I.1": 6, "I.2": 2, "I.3": 1, "II.1": 4}),
        unmatched_codes=Counter(),
    )
    h = cov.histogram
    assert h == {"0": 6, "1-2": 2, "3-4": 1, "5+": 1}
    assert sum(h.values()) == cov.podstawowy_topics
