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

## Manifest

`podstawa_matematyka.pdf` / `matematyka.pdf` should **not** be listed in
`sources/MANIFEST.md` as an authoritative `PODSTAWA_PROGRAMOWA` source — it is
superseded. If kept at all, it belongs as `OTHER` / reference, clearly marked
superseded. `DU_programowej_2024.pdf` stays as the `PODSTAWA_PROGRAMOWA` row
and is the curriculum authority.
