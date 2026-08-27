# Rough exercise coverage — podstawowy

**Signal:** the `zasady oceniania` cites the podstawa requirement codes each task tests. This is CKE's own mapping, parsed cheaply — **not** the M3 mapping agent. maj-2024 cites the superseded *wymagania egzaminacyjne 2024* (numbering mostly matches Dz.U. 2024; a few rows may be off).

Corpus: sessions 2203, 2209, 2305, 2312, 2405, 2505, 2605 (291 task→code citations, 9 leaf tasks with no parseable code).

## Two counts, deliberately

**primary** = the task's first-cited requirement (the one it mainly drills). **touches** = any requirement the task cites. A task that builds a system of equations *and* interprets a linear coefficient is one primary + one touch. The EXERCISES episode format wants five that **primarily** drill a requirement; touches are supporting material. Do not read the touches column as progress the primary column doesn't show (SPEC settled decision 10; `m3/mapping_multitopic_scan.md`).

| exercises per requirement | primarily drills | also touches |
|---|---|---|
| 0 | 14 | 12 |
| 1–2 | 21 | 15 |
| 3–4 | 20 | 15 |
| 5+ | 18 | 31 |

Covered as **primary** (≥1): **59 / 73**. At the EXERCISES 5-per-topic bar, **primary**: **18 / 73** (touches: 31).

## Requirements with 5+ exercises that primarily drill them

- `V.4` ×12 primary (+1 touch) — odczytuje z wykresu funkcji: dziedzinę, zbiór wartości, miejsca zerowe, przedziały monotoniczności, przedziały, w których funkcja przyjmuje wartości większe (nie mniejsze) lub mniejsze (nie większe) od danej liczby, największe i najmniejsze wartości funkcji (o ile istnieją) w danym przedziale domkniętym oraz argumenty, dla których wartości największe i najmniejsze są przez funkcję przyjmowane
- `XII.2` ×12 primary (+0 touch) — oblicza średnią arytmetyczną i średnią ważoną, znajduje medianę i dominantę
- `I.1` ×8 primary (+0 touch) — wykonuje działania (dodawanie, odejmowanie, mnożenie, dzielenie, potęgowanie, pierwiastkowanie, logarytmowanie) w zbiorze liczb rzeczywistych
- `I.2` ×8 primary (+0 touch) — przeprowadza proste dowody dotyczące podzielności liczb całkowitych i reszt z dzielenia, np.:
- `IX.2` ×8 primary (+0 touch) — posługuje się równaniami prostych na płaszczyźnie, w postaci kierunkowej i ogólnej, w tym wyznacza równanie prostej o zadanych własnościach (takich, jak np. przechodzenie przez dwa dane punkty, znany współczynnik kierunkowy, równoległość do innej prostej)
- `II.1` ×7 primary (+0 touch) — stosuje wzory skróconego mnożenia na kwadrat sumy, kwadrat różnicy i różnicę kwadratów
- `V.5` ×7 primary (+0 touch) — interpretuje współczynniki występujące we wzorze funkcji liniowej
- `VIII.5` ×7 primary (+1 touch) — stosuje własności kątów wpisanych i środkowych
- `III.5` ×7 primary (+2 touch) — rozwiązuje równania wielomianowe dla wielomianów doprowadzonych do postaci iloczynowej
- `XII.1` ×7 primary (+1 touch) — oblicza prawdopodobieństwo w modelu klasycznym
- `VII.1` ×7 primary (+0 touch) — wykorzystuje definicje funkcji: sinus, cosinus i tangens dla kątów od 0° do 180°, w szczególności wyznacza wartości funkcji trygonometrycznych dla kątów 30°, 45°, 60°
- `XI.2` ×6 primary (+1 touch) — zlicza obiekty, stosując reguły mnożenia i dodawania (także łącznie) dla dowolnej liczby czynności, np.:
- `VI.1` ×6 primary (+0 touch) — oblicza wyrazy ciągu określonego wzorem ogólnym
- `IX.3` ×6 primary (+0 touch) — oblicza odległość dwóch punktów w układzie współrzędnych
- `VII.2` ×6 primary (+2 touch) — korzysta z jedynki trygonometrycznej oraz z definicji tangensa jako ilorazu sinusa i cosinusa
- `X.2` ×5 primary (+1 touch) — posługuje się pojęciem kąta między prostą a płaszczyzną oraz pojęciem kąta dwuściennego między półpłaszczyznami
- `V.3` ×5 primary (+0 touch) — odczytuje i interpretuje wartości funkcji określonych za pomocą tabel, wykresów, wzorów itp., również w sytuacjach wielokrotnego użycia tego samego źródła informacji lub kilku źródeł jednocześnie
- `IV.2` ×5 primary (+0 touch) — stosuje układy równań do rozwiązywania zadań tekstowych

## Requirements with zero primary exercises (14)

`I.5`, `II.3`, `III.2`, `V.1`, `V.7`, `V.10`, `V.14`, `VIII.2`, `VIII.6`, `VIII.12`, `IX.5`, `X.3`, `X.6`, `XIII.1`

## Codes cited by a zasady but not a podstawowy topic

`III.6`×4, `II.6`×1, `II.5`×1

(rozszerzony codes, or maj-2024 numbering that diverged from Dz.U. 2024)

## Read

7 ingested papers give a **primary** exercise for 59 of 73 requirements; the EXERCISES five-per-topic bar is met (primary) for 18. Counting touches as well moves that to 31, but a touch is not what the format needs. 35 requirements still have two or fewer exercises that primarily drill them, and CKE publishes ~2 podstawowy sessions a year. Reading it straight (SPEC settled decision 10): the deterministic corpus is calibration and seed material, not supply. The Exercise Agent (M5, generation + symbolic verification) is load-bearing for the EXERCISES format. Harvested arkusze anchor difficulty and Matura-authentic phrasing; generated-and-verified exercises are the majority for most topics.
