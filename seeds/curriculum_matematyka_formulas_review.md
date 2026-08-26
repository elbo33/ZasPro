# Curriculum seed — formula review (M0.6)

`pdftotext` corrupts the maths in `DU_programowej_2024.pdf` (M0.5): every math-italic variable is doubled (`𝑥𝑥` for `𝑥`) and stacked fractions/superscripts collapse. So each requirement below has its prose in `name` and its formula hand-transcribed into `statement_latex` from the **rendered** PDF (pages 327–335 of `DU_programowej_2024.pdf`).

- **16 rows** where extraction changed the maths — verify these first.
- **4 rows** where extraction was clean but the formula is still given its own `statement_latex` for schema consistency.
- Verify each `statement_latex` against the **rendered appearance** column; open the PDF only if that is not enough.


## A. Extraction changed the maths (16)

### I.5 (podstawowy) — Liczby rzeczywiste

- **seed name:** stosuje monotoniczność potęgowania, w szczególności własności dla podstawy większej niż 1 oraz z przedziału (0, 1)
- **statement_latex:** `x<y \,\land\, a>1 \;\Rightarrow\; a^{x}<a^{y}; \qquad x<y \,\land\, 0<a<1 \;\Rightarrow\; a^{x}>a^{y}`
- **rendered in PDF:** inline: „jeśli x < y oraz a > 1, to aˣ < aʸ, zaś gdy x < y i 0 < a < 1, to aˣ > aʸ” — x, y, a italic; the a-terms have raised superscript exponents x and y
- **pdftotext gave:** `… to ax < ay, zaś gdy x < y i 0 < a < 1, to ax > ay`

### II.1 (podstawowy) — Wyrażenia algebraiczne

- **seed name:** stosuje wzory skróconego mnożenia na kwadrat sumy, kwadrat różnicy i różnicę kwadratów
- **statement_latex:** `(a+b)^{2}, \quad (a-b)^{2}, \quad a^{2}-b^{2}`
- **rendered in PDF:** „(a + b)², (a − b)², a² − b²” — superscript 2
- **pdftotext gave:** `(a + b)2, (a − b)2, a2 − b2`

### II.R4 (rozszerzony) — Wyrażenia algebraiczne

- **seed name:** stosuje podstawowe własności trójkąta Pascala oraz następujące własności współczynnika dwumianowego (symbolu Newtona)
- **statement_latex:** `\binom{n}{0}=1, \quad \binom{n}{1}=n, \quad \binom{n}{n-1}=n, \quad \binom{n}{k}=\binom{n}{n-k}, \quad \binom{n}{k}+\binom{n}{k+1}=\binom{n+1}{k+1}`
- **rendered in PDF:** five identities, each with binomial coefficients written vertically as (n over k) inside round brackets
- **pdftotext gave:** `(𝑛𝑛0) = 1, (𝑛𝑛1) = 𝑛𝑛, 𝑛𝑛 (𝑛𝑛−1 ) = 𝑛𝑛, (𝑛𝑛𝑘𝑘) = (𝑛𝑛−𝑘𝑘 𝑛𝑛 ), (𝑛𝑛𝑘𝑘) + (𝑘𝑘+1 𝑛𝑛 ) = (𝑛𝑛+1 𝑘𝑘+1 )`

### II.R5 (rozszerzony) — Wyrażenia algebraiczne

- **seed name:** korzysta ze wzorów na sumę i różnicę sześcianów, różnicę n-tych potęg oraz n-tą potęgę sumy i różnicy
- **statement_latex:** `a^{3}+b^{3}, \quad a^{3}-b^{3}, \quad a^{n}-b^{n}, \quad (a+b)^{n}, \quad (a-b)^{n}`
- **rendered in PDF:** „a³ + b³, a³ − b³, aⁿ − bⁿ, (a + b)ⁿ i (a − b)ⁿ” — superscript 3 and n
- **pdftotext gave:** `a3 + b3, a3 − b3, an − bn, (a + b)n i (a − b)n  [+ fragments of R6 bled in]`

### II.R6 (rozszerzony) — Wyrażenia algebraiczne

- **seed name:** dodaje i odejmuje wyrażenia wymierne w przypadkach nie trudniejszych niż podane przykłady
- **statement_latex:** `\frac{1}{x+1}-\frac{1}{x}; \qquad \frac{1}{x}+\frac{1}{x^{2}}+\frac{1}{x^{3}}; \qquad \frac{x+1}{x+2}+\frac{x-1}{x+1}`
- **rendered in PDF:** three example expressions, each a sum/difference of proper fractions (numerator stacked over denominator)
- **pdftotext gave:** `𝑥𝑥 +1 − 𝑥𝑥, 𝑥𝑥 + 𝑥𝑥 2 + 𝑥𝑥 3, 𝑥𝑥 + 2 + 𝑥𝑥 + 1`

### III.1 (podstawowy) — Równania i nierówności

- **seed name:** przekształca równania i nierówności w sposób równoważny, w tym równania wymierne prowadzące do równania liniowego
- **statement_latex:** `\frac{5}{x+1}=\frac{x+3}{2x-1}`
- **rendered in PDF:** „przekształca równoważnie równanie 5/(x+1) = (x+3)/(2x−1)” — two proper fractions either side of the equals sign
- **pdftotext gave:** `przekształca 5 𝑥𝑥 + 3 równoważnie równanie 𝑥𝑥 + 1 = 2𝑥𝑥−1`

### III.R7 (rozszerzony) — Równania i nierówności

- **seed name:** rozwiązuje równania wymierne, których licznik i mianownik są zapisane w postaci iloczynowej
- **statement_latex:** `\frac{V(x)}{W(x)} = 0`
- **rendered in PDF:** „równania wymierne postaci V(x)/W(x) = 0, gdzie wielomiany V(x) i W(x) są zapisane w postaci iloczynowej”
- **pdftotext gave:** `postaci 𝑉𝑉(𝑥𝑥)/𝑊𝑊(𝑥𝑥)= 0ǡ gdzie wielomiany 𝑉𝑉(𝑥𝑥) i 𝑊𝑊(𝑥𝑥)   [comma → U+01E1 ‘ǡ’]`

### IV.R1 (rozszerzony) — Układy równań

- **seed name:** rozwiązuje układy równań liniowych i kwadratowych z dwiema niewiadomymi, które można sprowadzić do równania kwadratowego lub liniowego i które nie są trudniejsze niż podany przykład
- **statement_latex:** `\begin{cases} x^{2}+y^{2}+ax+by=c \\ x^{2}+y^{2}+dx+ey=f \end{cases}`
- **rendered in PDF:** a two-equation system in a large brace, each equation of the form x² + y² + (linear terms) = const
- **pdftotext gave:** `𝑥𝑥 2 + 𝑦𝑦 2 + 𝑎𝑎𝑎𝑎 + 𝑏𝑏𝑏𝑏 = 𝑐𝑐  {  .  𝑥𝑥 2 + 𝑦𝑦 2 + 𝑑𝑑𝑑𝑑 + 𝑒𝑒𝑒𝑒 = 𝑓𝑓`

### V.12 (podstawowy) — Funkcje

- **seed name:** na podstawie wykresu funkcji y = f(x) szkicuje wykresy funkcji powstałych przez przesunięcie wzdłuż osi
- **statement_latex:** `y=f(x) \;\longrightarrow\; y=f(x-a), \quad y=f(x)+b`
- **rendered in PDF:** „y = f(x) szkicuje wykresy funkcji y = f(x − a), y = f(x) + b”
- **pdftotext gave:** `𝑦𝑦 = 𝑓𝑓(𝑥𝑥) szkicuje wykresy funkcji 𝑦𝑦 = 𝑓𝑓(𝑥𝑥 − 𝑎𝑎), 𝑦𝑦 = 𝑓𝑓(𝑥𝑥) + 𝑏𝑏`

### V.13 (podstawowy) — Funkcje

- **seed name:** posługuje się funkcją odwrotnie proporcjonalną, w tym jej wykresem, do opisu i interpretacji zagadnień związanych z wielkościami odwrotnie proporcjonalnymi
- **statement_latex:** `f(x)=\frac{a}{x}`
- **rendered in PDF:** „posługuje się funkcją f(x) = a/x” — a stacked over x as a fraction
- **pdftotext gave:** `posługuje się funkcją 𝑓𝑓(𝑥𝑥) = 𝑥𝑥   [the ‘a’ and the fraction bar are GONE]`

### V.R1 (rozszerzony) — Funkcje

- **seed name:** na podstawie wykresu funkcji y = f(x) rysuje wykresy funkcji powstałych przez odbicie względem osi
- **statement_latex:** `y=f(x) \;\longrightarrow\; y=-f(x), \quad y=f(-x)`
- **rendered in PDF:** „y = f(x) rysuje wykresy funkcji y = −f(x), y = f(−x)”
- **pdftotext gave:** `𝑦𝑦 = 𝑓𝑓(𝑥𝑥) rysuje wykresy funkcji 𝑦𝑦 = −𝑓𝑓(𝑥𝑥), 𝑦𝑦 = 𝑓𝑓(−𝑥𝑥)`

### V.R3 (rozszerzony) — Funkcje

- **seed name:** dowodzi monotoniczności funkcji zadanej wzorem, jak w przykładzie: wykazanie, że dana funkcja wymierna jest monotoniczna w podanym przedziale
- **statement_latex:** `f(x)=\frac{x-1}{x+2} \quad \text{monotoniczna w} \quad (-\infty,\,-2)`
- **rendered in PDF:** „wykaż, że funkcja f(x) = (x−1)/(x+2) jest monotoniczna w przedziale (−∞, −2)” — (x−1) stacked over (x+2)
- **pdftotext gave:** `wykaż, że funkcja 𝑥𝑥−1 𝑓𝑓(𝑥𝑥) = 𝑥𝑥+2 jest monotoniczna w przedziale (−∞, −2)`

### VI.R1 (rozszerzony) — Ciągi

- **seed name:** oblicza granice ciągów, korzystając z granic ciągów wzorcowych (typu 1/n oraz n-tego pierwiastka z a) oraz twierdzeń o granicy sumy, różnicy, iloczynu i ilorazu ciągów zbieżnych, a także twierdzenia o trzech ciągach
- **statement_latex:** `\tfrac{1}{n}, \quad \sqrt[n]{a}`
- **rendered in PDF:** „granic ciągów typu 1/n, ⁿ√a” — 1 stacked over n; and an n-th root of a (small n above the radical)
- **pdftotext gave:** `granic ciągów typu 𝑛𝑛, 𝑛𝑛√𝑎𝑎   [the ‘1’ numerator is GONE; ⁿ√a lost its index]`

### VII.2 (podstawowy) — Trygonometria

- **seed name:** korzysta z jedynki trygonometrycznej oraz z definicji tangensa jako ilorazu sinusa i cosinusa
- **statement_latex:** `\sin^{2}\alpha+\cos^{2}\alpha=1; \qquad \operatorname{tg}\alpha=\frac{\sin\alpha}{\cos\alpha}`
- **rendered in PDF:** „sin²α + cos²α = 1, tg α = sin α / cos α” — the tangent identity has sin α stacked over cos α
- **pdftotext gave:** `sin2 𝛼𝛼 + cos 2 𝛼𝛼 = 1, tg 𝛼𝛼 = cos 𝛼𝛼   [the ‘sin α’ numerator is GONE]`

### VII.3 (podstawowy) — Trygonometria

- **seed name:** stosuje twierdzenie cosinusów oraz wzór na pole trójkąta wyrażone przez dwa boki i sinus kąta między nimi
- **statement_latex:** `P=\tfrac{1}{2}\,a\,b\,\sin\gamma`
- **rendered in PDF:** „wzór na pole trójkąta P = ½ · a · b · sin γ” — one-half as a fraction
- **pdftotext gave:** `wzór na pole trójkąta 𝑃𝑃 = 2 ⋅ 𝑎𝑎 ⋅ 𝑏𝑏 ⋅ sin 𝛾𝛾   [½ became 2 — the formula is now wrong]`

### IX.4 (podstawowy) — Geometria analityczna na płaszczyźnie kartezjańskiej

- **seed name:** posługuje się równaniem okręgu w postaci kanonicznej
- **statement_latex:** `(x-a)^{2}+(y-b)^{2}=r^{2}`
- **rendered in PDF:** „(x − a)² + (y − b)² = r²” — superscript 2 throughout
- **pdftotext gave:** `(𝑥𝑥 − 𝑎𝑎)2 + (𝑦𝑦 − 𝑏𝑏)2 = 𝑟𝑟 2`


## B. Extraction clean, transcribed anyway (4)

### I.7 (podstawowy) — Liczby rzeczywiste

- **seed name:** stosuje interpretację geometryczną i algebraiczną wartości bezwzględnej, rozwiązuje proste równania z wartością bezwzględną
- **statement_latex:** `|x + 4| = 5`
- **rendered in PDF:** „rozwiązuje równania typu: |x + 4| = 5”
- **pdftotext gave:** `rozwiązuje równania typu: |x + 4| = 5`

### II.R1 (rozszerzony) — Wyrażenia algebraiczne

- **seed name:** dzieli wielomian jednej zmiennej przez dwumian postaci x minus a
- **statement_latex:** `W(x) : (x - a)`
- **rendered in PDF:** „dzieli wielomian jednej zmiennej W(x) przez dwumian postaci x − a”
- **pdftotext gave:** `dzieli wielomian jednej zmiennej W(x) przez dwumian postaci x − a`

### III.5 (podstawowy) — Równania i nierówności

- **seed name:** rozwiązuje równania wielomianowe dla wielomianów doprowadzonych do postaci iloczynowej
- **statement_latex:** `W(x) = 0`
- **rendered in PDF:** „równania wielomianowe postaci W(x) = 0”
- **pdftotext gave:** `równania wielomianowe postaci W(x) = 0`

### III.R1 (rozszerzony) — Równania i nierówności

- **seed name:** rozwiązuje równania i nierówności wielomianowe dla wielomianów doprowadzonych do postaci iloczynowej (także przez wyłączanie czynnika lub grupowanie)
- **statement_latex:** `W(x)=0; \qquad W(x)>0,\; W(x)\ge 0,\; W(x)<0,\; W(x)\le 0`
- **rendered in PDF:** „W(x) = 0 oraz nierówności wielomianowe typu: W(x) > 0, W(x) ≥ 0, W(x) < 0, W(x) ≤ 0”
- **pdftotext gave:** `W(x) = 0 oraz nierówności wielomianowe typu: W(x) > 0, W(x) ≥ 0, W(x) < 0, W(x) ≤ 0`
