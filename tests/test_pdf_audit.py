"""M0.5 diacritic assertion, against a deliberately corrupted fixture (SPEC §18)."""

from zaspro.m0.pdf_audit import diacritic_ratio, diacritics_corrupt

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
