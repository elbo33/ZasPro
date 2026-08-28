# M5 Step 1 — placing the 263 corpus exercises on teaching sections

**No generation. No verification. No schema change.** This records where the
existing exercises land on the 62 teaching sections, and what they look like as
raw material against the M5 per-section target.

## The per-section target (for reference)

| slot | count | shape |
|---|---|---|
| THEORY | supporting examples | easy, introduce the topic |
| EXERCISES | 5 | ramp, easy → hard |
| COMMON_MISTAKES | 5 | one misconception each, with a small worked example of the error |
| CHALLENGE | 3 | each harder than the last |

62 sections → ~800 problems. The corpus supplies 263.

## Placement rule

* **60 sections map 1:1 from their requirement code** — the exercise's PRIMARY
  `exercise_topics` row → the section that carries that code. Mechanical,
  re-derivable at any time (`section_requirements ⋈ exercise_topics` where
  `role = PRIMARY`).
* **X.5 and III.4 span several sections, all carrying the same code.** Every
  exercise under those two codes is assigned below by reading what it is about,
  not by splitting evenly.

Difficulty was judged from `points_available` (the `difficulty` column is
unpopulated — an M5 field). Working scale: **1 pkt** = multiple-choice / single
step / easy · **2 pkt** = short open, one real step · **3 pkt** = multi-step
open · **4 pkt** = extended, several linked steps.

## X.5 — 8 exercises, split by solid

| exercise | source | pkt | about | → section |
|---|---|---|---|---|
| 25 | 2209 | 3 | height of a triangular pyramid from edge lengths | `graniastoslupy-i-ostroslupy` |
| 26 | 2305 | 4 | regular quadrilateral pyramid — volume + total surface area | `graniastoslupy-i-ostroslupy` |
| 26 | 2505 | 1 | space diagonal of a cube from its volume | `graniastoslupy-i-ostroslupy` |
| 26 | 2312 | 3 | slant height of a regular quadrilateral pyramid from its volume | `graniastoslupy-i-ostroslupy` |
| 25.1 | 2405 | 1 | lateral surface area of a regular quadrilateral prism | `graniastoslupy-i-ostroslupy` |
| 27 | 2605 | 2 | volume of a regular quadrilateral pyramid from a diagonal + angle | `graniastoslupy-i-ostroslupy` |
| 25 | 2505 | 3 | volume of a cone from slant + apex angle | `stozek` |
| 28 | 2605 | 1 | ratio of cone volume to cylinder volume (equal heights, r doubled) | `stozek` (also touches `walec`) |

Result: `graniastoslupy-i-ostroslupy` 6 · `stozek` 2 · `walec` 0 · `kula` 0.
**No standalone cylinder or sphere exercise exists in the 7-paper corpus.**

## III.4 — 2 exercises, both inequalities

| exercise | source | pkt | about | → section |
|---|---|---|---|---|
| 10 | 2505 | 2 | solve `3(2x² + 1) < 11x` | `nierownosci-kwadratowe` |
| 10 | 2605 | 2 | solve `3x² + 4x ≥ 6x + 8` | `nierownosci-kwadratowe` |

Result: `nierownosci-kwadratowe` 2 · `rownania-kwadratowe` 0. Quadratic
*equations* appear only as a step inside larger tasks, never as a standalone
exam exercise here.

## Per-section count and difficulty spread

`n` = corpus exercises placed on the section. `1 2 3 4` = count at each point
value. `·k` = k exercises with no parsed point value. Status: **ok** ≥ 5 ·
**thin** 1–4 · **EMPTY** 0.

| # | section | code(s) | n | 1 | 2 | 3 | 4 | | status |
|--:|---|---|--:|--:|--:|--:|--:|--|---|
| 1 | dzialania-liczby-rzeczywiste | I.1, I.6 | 0 | | | | | | **EMPTY** |
| 2 | wartosc-bezwzgledna | I.7 | 5 | 5 | | | | | ok |
| 3 | pierwiastki-dowolnego-stopnia | I.3 | 1 | 1 | | | | | thin |
| 4 | prawa-dzialan-potegi-pierwiastki | I.4 | 9 | 9 | | | | | ok |
| 5 | monotonicznosc-potegowania | I.5 | 0 | | | | | | **EMPTY** |
| 6 | logarytm-i-jego-wlasnosci | I.9 | 7 | 7 | | | | | ok |
| 7 | procent-skladany | I.8 | 3 | 3 | | | | | thin |
| 8 | dowody-podzielnosci | I.2 | 7 | | 7 | | | | ok |
| 9 | wzory-skroconego-mnozenia | II.1 | 6 | 5 | 1 | | | | ok |
| 10 | wylaczanie-wspolnego-czynnika | II.3 | 0 | | | | | | **EMPTY** |
| 11 | dzialania-na-wielomianach | II.2 | 1 | 1 | | | | | thin |
| 12 | postac-iloczynowa-rownania-wielomianowe | III.5 | 10 | 6 | | 4 | | | ok |
| 13 | wyrazenia-wymierne | II.4 | 3 | 3 | | | | | thin |
| 14 | przeksztalcanie-rownan-wymierne-do-liniowego | III.1 | 4 | 4 | | | | | thin |
| 15 | rownania-nierownosci-liniowe | III.2, III.3 | 3 | 3 | | | | | thin |
| 16 | uklady-rownan-liniowych | IV.1, IV.2 | 9 | 5 | 4 | | | | ok |
| 17 | rownania-kwadratowe | III.4 | 0 | | | | | | **EMPTY** |
| 18 | nierownosci-kwadratowe | III.4 | 2 | | 2 | | | | thin |
| 19 | pojecie-funkcji-wartosci | V.1, V.2, V.3 | 4 | 3 | | | | ·1 | thin |
| 20 | wlasnosci-funkcji-z-wykresu | V.4 | 14 | 10 | 2 | | 1 | ·1 | ok |
| 21 | funkcja-liniowa | V.5, V.6 | 11 | 9 | 1 | | | ·1 | ok |
| 22 | funkcja-kwadratowa-wykres-postacie | V.7, V.8, V.9 | 16 | 7 | 2 | 1 | 1 | ·5 | ok |
| 23 | funkcja-kwadratowa-wartosci-w-przedziale | V.10 | 1 | | 1 | | | | thin |
| 24 | zastosowania-funkcji-optymalizacja | V.11, XIII.1 | 10 | 2 | | | 5 | ·3 | ok |
| 25 | przeksztalcenia-wykresow | V.12 | 3 | 2 | 1 | | | | thin |
| 26 | funkcja-odwrotnie-proporcjonalna | V.13 | 0 | | | | | | **EMPTY** |
| 27 | funkcje-wykladnicza-logarytmiczna | V.14 | 3 | 2 | | | | ·1 | thin |
| 28 | ciag-wzor-ogolny | VI.1 | 7 | 5 | | | | ·2 | ok |
| 29 | ciagi-rekurencyjne-monotonicznosc | VI.2, VI.3 | 3 | 2 | | | | ·1 | thin |
| 30 | ciag-arytmetyczny | VI.4, VI.5 | 10 | 7 | 2 | 1 | | | ok |
| 31 | ciag-geometryczny | VI.6 | 2 | 1 | | 1 | | | thin |
| 32 | zastosowania-ciagow | VI.7 | 4 | 3 | | 1 | | | thin |
| 33 | trojkaty-prostokatne-trygonometria | VII.4 | 6 | 5 | | | | ·1 | ok |
| 34 | sinus-cosinus-tangens-kata | VII.1 | 2 | 1 | 1 | | | | thin |
| 35 | jedynka-trygonometryczna | VII.2 | 8 | 7 | 1 | | | | ok |
| 36 | twierdzenie-cosinusow-pole-trojkata | VII.3 | 3 | 2 | 1 | | | | thin |
| 37 | okrag-cieciwy-i-styczne | VIII.1 | 1 | | 1 | | | | thin |
| 38 | kat-wpisany-i-srodkowy | VIII.5 | 7 | 7 | | | | | ok |
| 39 | wycinek-kola-luk | VIII.6 | 0 | | | | | | **EMPTY** |
| 40 | rodzaje-trojkatow-twierdzenie-odwrotne | VIII.2 | 0 | | | | | | **EMPTY** |
| 41 | wlasnosci-czworokatow | VIII.4 | 0 | | | | | | **EMPTY** |
| 42 | wielokaty-foremne | VIII.3 | 1 | 1 | | | | | thin |
| 43 | punkty-szczegolne-trojkata | VIII.10 | 1 | 1 | | | | | thin |
| 44 | twierdzenie-talesa | VIII.7 | 1 | 1 | | | | | thin |
| 45 | cechy-podobienstwa-trojkatow | VIII.8 | 4 | 4 | | | | | thin |
| 46 | pola-obwody-figur-podobnych | VIII.9 | 2 | 1 | 1 | | | | thin |
| 47 | dowody-geometryczne | VIII.11 | 1 | | 1 | | | | thin |
| 48 | trygonometria-w-figurach-plaskich | VIII.12 | 3 | 3 | | | | | thin |
| 49 | proste-odleglosci-uklad-wspolrzednych | IX.1, IX.2, IX.3 | 16 | 14 | 2 | | | | ok |
| 50 | rownanie-okregu | IX.4 | 4 | 4 | | | | | thin |
| 51 | symetrie-przesuniecie-uklad-wspolrzednych | IX.5 | 0 | | | | | | **EMPTY** |
| 52 | proste-plaszczyzny-katy-w-przestrzeni | X.1, X.2 | 3 | 3 | | | | | thin |
| 53 | katy-w-brylach | X.3, X.4 | 2 | 1 | | | | ·1 | thin |
| 54 | graniastoslupy-i-ostroslupy | X.5 | 6 | 2 | 1 | 2 | 1 | | ok |
| 55 | walec | X.5 | 0 | | | | | | **EMPTY** |
| 56 | stozek | X.5 | 2 | 1 | | 1 | | | thin |
| 57 | kula | X.5 | 0 | | | | | | **EMPTY** |
| 58 | bryly-podobne | X.6 | 2 | 2 | | | | | thin |
| 59 | zliczanie-obiektow | XI.1 | 1 | 1 | | | | | thin |
| 60 | regula-mnozenia-i-dodawania | XI.2 | 6 | 5 | 1 | | | | ok |
| 61 | prawdopodobienstwo-klasyczne | XII.1 | 8 | 4 | 3 | 1 | | | ok |
| 62 | srednia-mediana-dominanta | XII.2 | 15 | 10 | 2 | | | ·3 | ok |

**263 placed, 0 unplaced.** 21 sections at ≥ 5 · 30 at 1–4 · **11 at 0**.

The 11 empty: `dzialania-liczby-rzeczywiste`, `monotonicznosc-potegowania`,
`wylaczanie-wspolnego-czynnika`, `rownania-kwadratowe`,
`funkcja-odwrotnie-proporcjonalna`, `wycinek-kola-luk`,
`rodzaje-trojkatow-twierdzenie-odwrotne`, `wlasnosci-czworokatow`,
`symetrie-przesuniecie-uklad-wspolrzednych`, `walec`, `kula`.

## What the 263 look like as raw material

**They are overwhelmingly the easy end.** Point spread across the 263:

| pkt | n | share | reads as |
|---|--:|--:|---|
| 1 | 185 | 70% | multiple-choice / single step — easy |
| 2 | 38 | 14% | short open, one real step — lower-mid |
| 3 | 12 | 5% | multi-step open — upper-mid |
| 4 | 8 | 3% | extended, linked steps — hard |
| — | 20 | 8% | no parsed point value |

**The hard end is thin and concentrated.** Only **20 exercises at 3–4 pkt**,
across ~9 sections:

* `zastosowania-funkcji-optymalizacja` — 5 × 4 pkt (all of XIII.1's tasks)
* `postac-iloczynowa-rownania-wielomianowe` — 4 × 3 pkt
* `graniastoslupy-i-ostroslupy` — 2 × 3 pkt + 1 × 4 pkt
* `stozek` — 1 × 3 pkt
* `wlasnosci-funkcji-z-wykresu`, `funkcja-kwadratowa-wykres-postacie` — 1 × 4 pkt each
* `ciag-arytmetyczny`, `ciag-geometryczny`, `zastosowania-ciagow`,
  `prawdopodobienstwo-klasyczne` — 1 × 3 pkt each

**53 of the 62 sections have no 3–4 pkt exercise at all.**

### Implication for the M5 targets

* **THEORY support examples** (easy) and the **bottom rungs of EXERCISES**: the
  corpus covers these well for the 51 non-empty sections — 185 one-pointers is
  plenty of easy material to seed from, adapt, or use as models.
* **Top of the EXERCISES ramp and all of CHALLENGE** (3 genuinely hard problems
  per section = 186): essentially all generation. The corpus contributes ~20
  hard problems, ~11% of the CHALLENGE need, and they sit in 9 sections. The
  other 53 sections start CHALLENGE from nothing.
* **COMMON_MISTAKES** is independent of this corpus — the misconceptions come
  from the approved section specs (`knowledge/sections/*.yaml`, 629 of them);
  M5 only needs to attach a small worked example of each error, which is
  generation regardless.
* The **11 empty sections** need the full EXERCISES + CHALLENGE set generated,
  including the easy end.

### Not used here

The 421 SECONDARY `exercise_topics` rows (an exercise that touches a code
without it being primary) are a secondary pool that could lift some thin
sections, at the cost of noisier fit. Left out of this placement; available if a
thin section needs padding before generation.
