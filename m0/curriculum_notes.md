# M0.6 — Curriculum source verification

## Decision: `matematyka.pdf` is DISCARDED; the tree is built from Dz.U. 2024 poz. 1019

SPEC M0.6 required checking the CKE maths-only extract
(`https://cke.gov.pl/images/_EGZAMIN_MATURALNY_OD_2015/Formula_2023/podstawa_programowa/matematyka.pdf`,
saved as `sources/raw/matematyka.pdf`) against Dz.U. 2024 poz. 1019 before use,
because the `_OD_2015` URL path is suspicious. **The requirement text diverges.
Per SPEC ("If they diverge, the Dz.U. text wins and this shortcut is
discarded"), `matematyka.pdf` is not used.**

`matematyka.pdf` is the 2018/2019 *"Podstawa programowa … z komentarzem"* (it
bundles three curricula — 4-letnie LO / 5-letnie technikum, branżowa I stopnia,
branżowa II stopnia — plus authors' commentary). It predates the 28 June 2024
amendment.

### Spot-check (section I, "Liczby rzeczywiste", zakres podstawowy)

Section and requirement **numbering** matches (I.1–I.9, same topics in the same
order). Requirement **text** does not:

| code | `matematyka.pdf` | Dz.U. 2024 poz. 1019 | |
|---|---|---|---|
| I.2 b) | "jeśli liczba przy dzieleniu przez **5** daje resztę 3, to jej **trzecia potęga** przy dzieleniu przez 5 daje resztę 2" | "jeśli liczba przy dzieleniu przez **4** daje resztę 3, to **nie jest kwadratem liczby całkowitej**" | ✗ diverges |
| I.7 | "rozwiązuje **równania i nierówności** typu: \|x + 4\| = 5, \|x − 2\| < 3, \|x + 3\| ≥ 4" | "rozwiązuje **równania** typu: \|x + 4\| = 5" | ✗ diverges |
| II.1 | wzory skróconego mnożenia up to `aⁿ − bⁿ` in **zakres podstawowy** | only `(a+b)²`, `(a−b)²`, `a²−b²` in podstawowy; the rest moved to **zakres rozszerzony** (II.R5) | ✗ diverges |

The pattern is consistent: the 2024 amendment **trimmed** zakres podstawowy
(fewer / simpler requirements) and shifted material into zakres rozszerzony.
`matematyka.pdf` still carries the heavier pre-amendment podstawowy.

### Cross-checks that DO hold (Dz.U. 2024 ↔ CKE usage)

The `official_requirement_code` scheme in the seed matches how CKE's
`zasady oceniania` cites the curriculum. From
`MMAP-P0-100-2605-zasady.pdf`:

- `VIII.10)` → "wskazuje podstawowe punkty szczególne w trójkącie …" — matches
  Dz.U. 2024 VIII.10.
- `IX.3)` → "oblicza odległość dwóch punktów …" — matches Dz.U. 2024 IX.3.
- `IX.1)` → "… znajduje wspólny punkt dwóch prostych …" — matches Dz.U. 2024 IX.1.

## The seed

`seeds/curriculum_matematyka.yaml`, extracted from
`sources/raw/DU_programowej_2024.pdf` ("Treści nauczania – wymagania
szczegółowe", liceum ogólnokształcące / technikum):

- 13 thematic units (I–XIII)
- 73 zakres-podstawowy requirements, 46 zakres-rozszerzony additions, 4
  sub-points (I.2 a/b, XI.2 a/b) — ~132 nodes
- `rozszerzony` codes carry an `R` (`I.R1`) so they stay unique next to the
  `podstawowy` codes; `rozszerzony` is podstawowy + "a ponadto" additions, not
  a separate tree (SPEC §5, M0.6)

**Status: DRAFT.** Extracted semi-manually with a one-off scaffold
(`zaspro.m0.curriculum_seed`, not a pipeline) and checked against the
regulation text. Every node still needs node-by-node human verification before
M1 seeds the `units` / `topics` tables from it.

### Extraction of the formulae cannot be trusted

`pdftotext` corrupts the maths in `DU_programowej_2024.pdf` (M0.5,
`m0/pdf_audit.md`): the maths font's ToUnicode maps every italic variable to a
two-codepoint sequence, so 54% of Mathematical Alphanumeric Symbols come out
**doubled** (`𝑥𝑥` for `𝑥`), and stacked fractions and superscripts collapse
with it. Measured damage in the curriculum text:

| code | rendered in PDF | pdftotext gave | effect |
|---|---|---|---|
| VII.3 | `P = ½ · a · b · sin γ` | `P = 2 · a · b · sin γ` | ½ → 2, **formula now wrong** |
| V.13 | `f(x) = a/x` | `f(x) = x` | coefficient and bar gone |
| VI.R1 | `typu 1/n, ⁿ√a` | `typu n, n√a` | `1` numerator gone |
| VII.2 | `tg α = sin α / cos α` | `tg α = cos α` | numerator gone |
| I.5 | `aˣ < aʸ` | `ax < ay` | superscripts flattened |
| II.R4 | five `(n over k)` identities | `(𝑛𝑛0) = 1, …` | structure destroyed |

**Consequence.** The seed separates prose from maths:

* `name` — the requirement prose, plain text (M1 seeds the tree from this).
* `statement_latex` — the formula, **hand-transcribed from the rendered PDF**
  (`DU_programowej_2024.pdf` pages 327–335), not from the extracted text.
  20 rows have one; a `name` with no `statement_latex` carries no formula.

### Transcription convention for `statement_latex`

`statement_latex` is the notation reference every downstream episode inherits,
so it is written to parse unambiguously, not merely to render. Applied to all
20 formula rows:

| rule | write | not |
|---|---|---|
| delimiters that enclose an operator are explicit and sized | `\left\| x+4 \right\|`, `\left( a+b \right)^{2}` | `\|x+4\|`, `(a+b)^{2}` |
| fractions | `\frac{a}{x}` | `a/x` |
| roots | `\sqrt[n]{a}` | `ⁿ√a` |
| Newton symbol | `\binom{n}{k}` | `(n over k)` ad hoc |
| Polish function names | `\tg`, `\ctg` | `\tan`, `\cot` |
| explicit multiplication | `\cdot` | `·`, thin space |
| inline half-height fraction | `\tfrac{1}{2}` | `\frac` |

Bare pipes are valid but ambiguous to a parser — the M0.3 study hit exactly
this with `|BC|`. Plain `(x)` is kept only for a single-symbol function
argument (`f(x)`, `W(x)`); anything enclosing an operator gets `\left…\right`.

**Renderer preamble.** `\tg` and `\ctg` are **not** standard LaTeX. A renderer
consuming `statement_latex` must declare:

```latex
\DeclareMathOperator{\tg}{tg}
\DeclareMathOperator{\ctg}{ctg}
```

Everything else in the 20 rows — `\binom`, `\tfrac`, `\begin{cases}`, `\land`,
`\Rightarrow`, `\longrightarrow`, `\sqrt[n]`, `\le`, `\ge`, `\cdot` — is
standard `amsmath` / base LaTeX. Only `\tg` is used in the current rows (VII.2);
`\ctg` is listed because downstream trigonometry content will need it.

`tests/test_seed_latex.py` compiles all 20 with `pdflatex` and this preamble on
every run (it skips where TeX is not installed).

### Review sheets

* `seeds/curriculum_matematyka_review.md` — all 132 nodes in Dz.U. order,
  seed `name` beside the `pdftotext` span; formula rows marked **⚑**.
* `seeds/curriculum_matematyka_formulas_review.md` — the 20 formula rows only:
  `statement_latex`, a description of the rendered PDF appearance, and the
  corrupt extraction, so the transcriptions can be checked without opening the
  PDF per line. 16 of the 20 were corrupted; verify those first.

## Manifest

`podstawa_matematyka.pdf` / `matematyka.pdf` should **not** be listed in
`sources/MANIFEST.md` as an authoritative `PODSTAWA_PROGRAMOWA` source — it is
superseded. If kept at all, it belongs as `OTHER` / reference, clearly marked
superseded. `DU_programowej_2024.pdf` stays as the `PODSTAWA_PROGRAMOWA` row
and is the curriculum authority.
