# M4 Step 1 — Teaching tree proposal (Matura podstawowa)

**Status: proposal for review. Not a seed.** Approve / edit the section list and
order; it then becomes a committed curriculum seed and Step 2 (per-section
knowledge) runs against it.

## What this is

A teaching layer above the 73 `official_requirement_code`s — the sequence a
course would be taught in, regrouped for teaching rather than mirroring the 13
`podstawa programowa` units. **50 sections**, roughly lesson-sized (mostly one
requirement each, a few thin ones paired), ordered so prerequisites come first.
Every requirement maps to exactly one section; the coverage table at the end
lists all 73, so coverage against the podstawa stays provable.

The two "Zadania…" sections from the earlier draft (word problems on systems;
optimisation problems) are gone — solving problems is applied practice, not a
distinct knowledge unit. Their requirement codes are folded into the nearest
substantive section: `IV.2` into section 15 (systems), `XIII.1` into section 22
(applications of linear/quadratic functions).

## Inputs used — and two gaps

* **The 73 podstawowy requirements** (DB, seeded from Dz.U. 2024 poz. 1019) —
  used in full.
* **`docs/reference/matemaks-structure.md` is still empty (0 bytes).** This draft
  used general knowledge of the matemaks.pl Matura-podstawowa course shape
  (≈14 chapters / ≈48 lessons; numbers → algebra → equations → functions →
  sequences → trigonometry → planimetry → analytic geometry → stereometry →
  combinatorics/probability/statistics) for teaching order and lesson sizing.
  Populate the file and I will re-check chapter divisions and granularity.
* **The informatory** (`Informator_EM2024_matematyka_pp_660.docx` and the PR
  equivalent) are in `sources/raw/` but not ingested into readable text, and
  were **not** consulted. Their value here is exam emphasis and task-type
  grouping. Say if you want them folded in before this becomes a seed.

## Notable regrouping vs the podstawa units

* Unit **V "Funkcje" (14 requirements)** spans eight sections: function concept,
  reading a graph, linear function, quadratic function (×2), applications
  (with optimisation), graph transformations, exponential/logarithmic functions.
* **Logarithms as algebra** (I.9) and **compound interest** (I.8) are pulled out
  of unit I; the exponential/logarithmic _functions_ (V.14) come later, after
  sequences.
* **Right-triangle trig** (VII.4) opens trigonometry; general angles (VII.1–2)
  and the law of cosines (VII.3) follow; trig then reappears inside planimetry
  (VIII.12).

---

## The sections, in teaching order

### Liczby rzeczywiste

**1. Działania w zbiorze liczb rzeczywistych; przedziały liczbowe** — `I.1`, `I.6`
The four operations plus powers, roots and logarithms as operations on real numbers; order of operations and estimation; number intervals and their marking on the axis.

**2. Wartość bezwzględna: interpretacja i proste równania** — `I.7`
Absolute value read geometrically (distance) and algebraically; solving simple equations with an absolute value.

**3. Pierwiastki dowolnego stopnia** — `I.3`
Properties of roots of any degree, including odd-degree roots of negative numbers; simplifying root expressions.

**4. Prawa działań na potęgach i pierwiastkach** — `I.4`
Rational exponents and the root–power link; the laws for multiplying, dividing and raising powers, and their counterparts for roots.

**5. Monotoniczność potęgowania** — `I.5`
How aˣ orders values of x: the direction is kept for base > 1 and reversed for base in (0, 1); comparing and estimating powers.

**6. Logarytm i jego własności** — `I.9`
Logarithm as the inverse of exponentiation; evaluating logarithms; the formulas for the logarithm of a product, a quotient and a power.

**7. Procent składany, lokaty i modele wykładnicze** — `I.8`
Powers and roots in practice: compound interest, deposit growth, loan cost, exponential decay; setting up and reading a growth/decay model.

**8. Dowody dotyczące podzielności liczb całkowitych** — `I.2`
Divisibility and remainders; representing integers by form (2k, 3k+1, …); short direct proofs about divisibility and parity. *(Order flexible — could sit at position 2.)*

### Wyrażenia algebraiczne

**9. Wzory skróconego mnożenia i przekształcanie wyrażeń** — `II.1`, `II.3`
(a ± b)² and a² − b² for expanding and factoring; taking a common monomial factor out of an algebraic sum.

**10. Działania na wielomianach** — `II.2`
Adding, subtracting and multiplying polynomials in one and several variables; ordering and collecting terms.

**11. Postać iloczynowa wielomianu i równania wielomianowe** — `III.5`
Bringing a polynomial to product form; solving polynomial equations once factored.

**12. Wyrażenia wymierne: dziedzina, mnożenie i dzielenie** — `II.4`
Domain of a rational expression; multiplying, dividing and simplifying rational expressions.

### Równania i nierówności

**13. Przekształcanie równań i nierówności; równania wymierne prowadzące do liniowego** — `III.1`
Equivalent transformations of equations and inequalities; solving rational equations that reduce to a linear one, with the domain condition.

**14. Równania liniowe sprzeczne i tożsamościowe; nierówności liniowe** — `III.2`, `III.3`
Recognising a contradictory and an identity linear equation; solving linear inequalities in one unknown and writing the solution set.

**15. Układy równań liniowych: rozwiązywanie, interpretacja i zastosowania** — `IV.1`, `IV.2`
Solving 2×2 linear systems; consistent, dependent and inconsistent systems as pairs of lines; translating a word problem into a system and interpreting the solution.

**16. Równania i nierówności kwadratowe** — `III.4`
Solving quadratic equations (factoring, discriminant, Vieta); solving quadratic inequalities from the sign of the parabola.

### Funkcje

**17. Pojęcie funkcji; obliczanie i odczytywanie wartości** — `V.1`, `V.2`, `V.3`
Function as a unique assignment given verbally, by table, graph, formula or piecewise; evaluating from a formula; reading and interpreting values from tables, graphs and formulas.

**18. Odczytywanie własności funkcji z wykresu** — `V.4`
From a graph: domain, range, zeros, intervals of monotonicity, intervals of constant sign, greatest and least value.

**19. Funkcja liniowa: współczynniki i wyznaczanie wzoru** — `V.5`, `V.6`
Meaning of a and b in y = ax + b; finding the formula from a graph or from stated properties; parallel and perpendicular lines via slope.

**20. Funkcja kwadratowa: wykres, postacie i wyznaczanie wzoru** — `V.7`, `V.8`, `V.9`
Sketching y = ax² + bx + c; interpreting coefficients in general, vertex and factored form; finding the formula from given information or a graph.

**21. Największa i najmniejsza wartość funkcji kwadratowej w przedziale** — `V.10`
Locating the extremum relative to a closed interval and reading off the greatest and least value on it.

**22. Zastosowania funkcji liniowej i kwadratowej; optymalizacja** — `V.11`, `XIII.1`
Using linear and quadratic functions to interpret geometric, physical and everyday problems; optimisation reducible to a quadratic — expressing the quantity as a quadratic function of one variable under constraints and reading the extremum.

**23. Przekształcenia wykresów i funkcja odwrotnie proporcjonalna** — `V.12`, `V.13`
Sketching graphs shifted along the axes from y = f(x); the inversely-proportional function y = a/x, its hyperbola, and modelling inversely-proportional quantities.

**24. Funkcje wykładnicza i logarytmiczna** — `V.14`
The exponential and logarithmic functions and their graphs; using them to describe and interpret growth, decay and scales.

### Ciągi

**25. Ciąg i jego wyrazy; wzór ogólny** — `VI.1`
Sequence as a function on the positive integers; computing terms from a general formula; the index–term correspondence.

**26. Ciągi rekurencyjne i monotoniczność ciągu** — `VI.2`, `VI.3`
Computing the first terms of a recursively defined sequence; deciding in simple cases whether a sequence is increasing or decreasing.

**27. Ciąg arytmetyczny: n-ty wyraz i suma** — `VI.4`, `VI.5`
Recognising an arithmetic sequence; the nth term and the sum of the first n terms.

**28. Ciąg geometryczny: n-ty wyraz i suma** — `VI.6`
Recognising a geometric sequence; the nth term and the sum of the first n terms.

**29. Zastosowania ciągów arytmetycznych i geometrycznych** — `VI.7`
Using sequence properties, arithmetic and geometric in particular, to solve problems, including practical ones.

### Trygonometria

**30. Rozwiązywanie trójkątów prostokątnych** — `VII.4`
sin, cos, tan in a right triangle; finding sides and angles from the given data.

**31. Sinus, cosinus i tangens kąta od 0° do 180°; jedynka trygonometryczna** — `VII.1`, `VII.2`
Values for 0°–180°, exact values for 30°/45°/60° and the reduction relationships; the Pythagorean identity; tan as sin ÷ cos.

**32. Twierdzenie cosinusów i pole trójkąta przez sinus** — `VII.3`
Law of cosines; area = ½·a·b·sin γ; choosing between them from the given data.

### Planimetria

**33. Okrąg: cięciwy, styczne, kąty wpisane i środkowe** — `VIII.1`, `VIII.5`
Radii, diameters, chords and tangent segments (with Pythagoras); inscribed and central angles and the relations between them.

**34. Wycinek koła i długość łuku** — `VIII.6`
Area of a circular sector and length of an arc from the central angle.

**35. Rodzaje trójkątów; twierdzenie odwrotne do twierdzenia Pitagorasa** — `VIII.2`
Classifying a triangle as acute, right or obtuse from its side lengths, using the converse of the Pythagorean theorem.

**36. Czworokąty i wielokąty foremne** — `VIII.3`, `VIII.4`
Angles and diagonals in rectangles, parallelograms, rhombi and trapezia; regular polygons and their basic properties.

**37. Punkty szczególne trójkąta** — `VIII.10`
Incentre, circumcentre, orthocentre and centroid: definitions and how to locate them.

**38. Twierdzenie Talesa i podobieństwo trójkątów** — `VIII.7`, `VIII.8`
Thales' theorem and its use; similarity criteria for triangles and their application.

**39. Pola i obwody figur podobnych** — `VIII.9`
Ratio of perimeters and ratio of areas of similar figures, and problems that use them.

**40. Dowody geometryczne** — `VIII.11`
Structuring a plane-geometry proof; typical arguments with congruent triangles, angles and the circle theorems.

**41. Trygonometria w figurach płaskich** — `VIII.12`
Using trig functions to find segment lengths and to compute areas of plane figures.

### Geometria analityczna

**42. Proste i odległości w układzie współrzędnych** — `IX.1`, `IX.2`, `IX.3`
Line equations in slope and general form; relative position of two lines and their common point; distance between two points and length of a segment.

**43. Równanie okręgu** — `IX.4`
Circle equation in canonical form; centre, radius and checking whether a point lies on the circle.

**44. Symetrie i przesunięcie w układzie współrzędnych** — `IX.5`
Images of circles and polygons under axis symmetries, central symmetry about the origin, and translation by a vector.

### Stereometria

**45. Proste, płaszczyzny i kąty w przestrzeni** — `X.1`, `X.2`
Relative position of lines in space, including skew perpendicular lines; angle between a line and a plane; dihedral angle.

**46. Kąty w graniastosłupach, ostrosłupach, walcach i stożkach** — `X.3`, `X.4`
Angles between edges, between edges and diagonals, and between faces in prisms and pyramids; angle of a cone's aperture and related angles in cylinders and cones, and computing them.

**47. Objętości, pola powierzchni i bryły podobne** — `X.5`, `X.6`
Volumes and surface areas of prisms, pyramids, cylinder, cone and sphere, including with trigonometry; ratio of volumes of similar solids.

### Kombinatoryka, prawdopodobieństwo, statystyka

**48. Kombinatoryka: zliczanie, reguła mnożenia i dodawania** — `XI.1`, `XI.2`
Counting objects in simple situations; the multiplication and addition rules, including used together, for any number of steps.

**49. Prawdopodobieństwo w modelu klasycznym** — `XII.1`
Equally likely outcomes; favourable versus all outcomes; complementary events.

**50. Średnia, mediana, dominanta** — `XII.2`
Arithmetic mean and weighted mean; median and mode, and reading them from a small data set.

---

## Coverage check — all 73 requirements, each assigned once

| Unit | Requirement → section |
|---|---|
| I (9) | I.1→1 · I.6→1 · I.7→2 · I.3→3 · I.4→4 · I.5→5 · I.9→6 · I.8→7 · I.2→8 |
| II (4) | II.1→9 · II.3→9 · II.2→10 · II.4→12 |
| III (5) | III.5→11 · III.1→13 · III.2→14 · III.3→14 · III.4→16 |
| IV (2) | IV.1→15 · IV.2→15 |
| V (14) | V.1→17 · V.2→17 · V.3→17 · V.4→18 · V.5→19 · V.6→19 · V.7→20 · V.8→20 · V.9→20 · V.10→21 · V.11→22 · V.12→23 · V.13→23 · V.14→24 |
| XIII (1) | XIII.1→22 |
| VI (7) | VI.1→25 · VI.2→26 · VI.3→26 · VI.4→27 · VI.5→27 · VI.6→28 · VI.7→29 |
| VII (4) | VII.4→30 · VII.1→31 · VII.2→31 · VII.3→32 |
| VIII (12) | VIII.1→33 · VIII.5→33 · VIII.6→34 · VIII.2→35 · VIII.3→36 · VIII.4→36 · VIII.10→37 · VIII.7→38 · VIII.8→38 · VIII.9→39 · VIII.11→40 · VIII.12→41 |
| IX (5) | IX.1→42 · IX.2→42 · IX.3→42 · IX.4→43 · IX.5→44 |
| X (6) | X.1→45 · X.2→45 · X.3→46 · X.4→46 · X.5→47 · X.6→47 |
| XI (2) | XI.1→48 · XI.2→48 |
| XII (2) | XII.1→49 · XII.2→50 |

**50 sections, 73 requirements, every code assigned exactly once.**

## Open questions for review

1. **Granularity.** 50 sections ≈ matemaks's 48 lessons. Comfortable, or pull
   toward its ~14 chapters (merge e.g. all of Planimetria)?
2. **Section 8** (`I.2`, integer proofs) — position 8, or move up to position 2?
3. Populate `docs/reference/matemaks-structure.md` and/or ingest the informatory
   before this is frozen as a seed?
