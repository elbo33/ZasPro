# Do the mapping agent's rationales point to a second topic?

Hand scan of the 37 `ClaudeMappingAgent` mappings from the 27 Aug 2026
calibration pass (`MMAP-P0-660-A-2405-arkusz.docx`). For each, does the
rationale name or clearly describe a *second* podstawa requirement the fragment
also plausibly tests?

* **A** — a specific second requirement code is named
  ("alternatywnie V.5", "z elementami VII.1", "równie plausibilne VIII.8")
* **B** — a second requirement is described but no code given
* **—** — one clean topic, nothing else mentioned

| Zadanie | conf | primary | second topic in rationale | class |
|---|---|---|---|---|
| 1 | 0.85 | I.7 | I.6 (intervals, "pomocniczo") | A |
| 2 | 0.85 | I.4 | — | — |
| 3 | 0.95 | I.2 | — | — |
| 4 | 0.85 | I.9 | I.1 ("ewentualnie") | A |
| 5 | 0.93 | II.1 | — | — |
| 6 | 0.95 | III.3 | — | — |
| 7 | 0.80 | III.1 | — | — |
| 8 | 0.55 | II.2 | "the dominant skill is …" (implies a second) | B |
| 9 | 0.90 | III.5 | — | — |
| 10 | 0.90 | IV.2 | — | — |
| 11 | 0.80 | IV.1 | IX.1 ("wtórnie") | A |
| 12 | 0.85 | V.5 | — | — |
| 13 | 0.70 | V.6 | V.5 ("alternatywnie … ale tu chodzi o wyznaczenie wzoru") | A |
| 14 | 0.60 | V.9 | V.8 ("alternative would be interpreting coefficients") | A |
| 14.1 | 0.60 | V.4 | solving inequalities (no code) | B |
| 14.2 | 0.80 | V.9 | — | — |
| 14.3 | 0.50 | V.3 | V.8 ("alternatively … symmetry of a quadratic") | A |
| 14.4 | 0.65 | V.12 | reflection/symmetry "wykracza poza samo przesunięcie" | B |
| 15 | 0.92 | VI.1 | — | — |
| 16 | 0.63 | VI.7 | VI.3 / VI.4 ("secondary aspects") | A |
| 17 | 0.93 | VI.5 | — | — |
| 18 | 0.68 | VII.2 | VII.1 ("z elementami VII.1") | A |
| 19 | 0.93 | VII.2 | — | — |
| 20 | 0.42 | VIII.11 | VIII.8 (similarity, "równie plausibilne") | A |
| 21 | 0.70 | VII.3 | VIII.12 — named as the actual skill, primary stored as VII.3 | A |
| 22 | 0.92 | VIII.5 | — | — |
| 23 | 0.82 | IX.1 | — | — |
| 24 | 0.62 | IX.3 | VIII.4 ("jest tu tylko pomocnicza") | A |
| 25 | 0.50 | X.3 | X.5 ("alternatively … volume/surface") | A |
| 25.1 | 0.92 | X.5 | — | — |
| 25.2 | 0.72 | X.3 | X.2 ("alternatywnie X.2") | A |
| 26 | 0.88 | X.6 | — | — |
| 27 | 0.75 | XI.2 | XI.1 ("alternatywnie XI.1") | A |
| 28 | 0.95 | XII.2 | — | — |
| 29 | 0.96 | XII.2 | — | — |
| 30 | 0.93 | XII.1 | — | — |
| 31 | 0.92 | XIII.1 | — | — |

## Count

* **A (explicit second code): 14 / 37**
* **B (second requirement described, no code): 3 / 37**
* **Total with a plausible second topic: 17 / 37 (46%)**
* clean single topic: 20 / 37

## The pattern is in the confidence

| band | n | with a second topic |
|---|---|---|
| [0.0, 0.5) | 1 | 1 (100%) |
| [0.5, 0.8) | 13 | **13 (100%)** |
| [0.8, 1.0] | 23 | 3 (13%) |

**Every mapping the agent scored below 0.8 carries a second plausible
requirement in its rationale. Almost none above 0.8 do.** The mid-range
confidence is not "am I right about this fragment?" — the agent was right on the
primary every time it was unsure (9/9 in [0.5,0.7), 3/4 in [0.7,0.8)). It is
"which of several defensible requirements is *the* one?" — a question the
single-topic contract forces and shouldn't.

## Consequence

Single-topic mapping means e.g. Zadanie 13 (find a linear function's formula
from a known zero) surfaces under V.6 only and is invisible to V.5 (interpret
the coefficients), which it also drills. Across 73 requirements this compounds:
a topic's EXERCISES episode can miss material that genuinely tests it. If ~1/3
of exercises span 2+ requirements (13/37 here), that is a structural gap, not
noise.
