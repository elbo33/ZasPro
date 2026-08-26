"""M0.5 diacritic + math-character assertions, against corrupted fixtures (SPEC §18)."""

from zaspro.m0.pdf_audit import (
    diacritic_ratio,
    diacritics_corrupt,
    math_alnum_stats,
    math_corrupt,
)

# ~healthy Polish prose (repeat to clear the 500-char body threshold)
_HEALTHY = (
    "Zdający posługuje się pojęciem funkcji liniowej. Rozwiązuje równania "
    "i nierówności, oblicza wartości bezwzględne, bada monotoniczność ciągu "
    "oraz wyznacza największą i najmniejszą wartość funkcji w przedziale. "
    "Świadomie stosuje własności potęg, pierwiastków i logarytmów. "
) * 4

# same text after a ToUnicode failure: Latin-Extended-A stripped to ASCII base
_CORRUPT = (
    _HEALTHY.replace("ą", "a").replace("ć", "c").replace("ę", "e")
    .replace("ł", "l").replace("ń", "n").replace("ó", "o")
    .replace("ś", "s").replace("ź", "z").replace("ż", "z")
    .replace("Ś", "S")
)


def test_healthy_polish_passes():
    r = diacritic_ratio(_HEALTHY)
    assert 0.05 <= r <= 0.15
    assert diacritics_corrupt(_HEALTHY) is False


def test_stripped_diacritics_flagged_as_corrupt():
    assert diacritic_ratio(_CORRUPT) == 0.0
    assert diacritics_corrupt(_CORRUPT) is True


def test_short_snippet_not_flagged():
    # too little text to conclude corruption from a low ratio
    assert diacritics_corrupt("Zadanie 1.") is False


# --- mathematical-character assertion (added after M0.6) ---------------------

# how DU_programowej_2024.pdf actually extracts: every math-italic var doubled
_MATH_OK = "rozwiazuje rownania wymierne postaci V(x)/W(x) = 0"
_MATH_DOUBLED = (
    "rozwiazuje rownania wymierne postaci \U0001d449\U0001d449(\U0001d465\U0001d465)"
    "/\U0001d44a\U0001d44a(\U0001d465\U0001d465) = 0"  # 𝑉𝑉(𝑥𝑥)/𝑊𝑊(𝑥𝑥)
) * 4
_MATH_PUA = "wartosc  w przedziale"


def test_clean_ascii_math_not_flagged():
    mas, doubled, pua = math_alnum_stats(_MATH_OK)
    assert (mas, doubled, pua) == (0, 0, 0)
    assert math_corrupt(_MATH_OK) is False


def test_doubled_math_alphanumeric_flagged():
    mas, doubled, pua = math_alnum_stats(_MATH_DOUBLED)
    assert mas > 20
    assert doubled / mas >= 0.15
    assert math_corrupt(_MATH_DOUBLED) is True


def test_private_use_glyph_flagged():
    assert math_alnum_stats(_MATH_PUA)[2] == 1
    assert math_corrupt(_MATH_PUA) is True


def test_incidental_math_symbols_not_flagged():
    # a couple of genuine 𝑥 with no doubling — normal, not corruption
    assert math_corrupt("wzor \U0001d465 + \U0001d466 = 1") is False
