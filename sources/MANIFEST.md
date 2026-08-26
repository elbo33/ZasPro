# Source manifest

Hand-authored. This is the seed data for the `sources` and `source_documents`
tables. Values here are authoritative; do not have a model regenerate them.

Licence status values:
- MATERIAL_URZEDOWY: published in Dziennik Ustaw, outside copyright (art. 4 pr. aut.)
- CKE_UNSPECIFIED: CKE publishes no reuse licence. Treat as restricted.

Notes:
- `matematyka.pdf` is the pre-2024 *"Podstawa programowa … z komentarzem"*
  edition (it bundles three curricula plus authors' commentary). It is
  **superseded by Dz.U. 2024 poz. 1019** and must not be used as a curriculum
  source. Checked in M0.6 against `DU_programowej_2024.pdf`; confirmed
  divergences: **I.2 b)** (reszta przez 5 / trzecia potęga → reszta przez 4 /
  kwadrat), **I.7** (równania i nierówności → równania only), **II.1** (wzory
  skróconego mnożenia up to `aⁿ − bⁿ` in podstawowy → only three, rest moved to
  rozszerzony). Kept as `OTHER` for traceability. Full spot-check in
  `m0/curriculum_notes.md`.

| file | title | publisher | source_type | session | level | variant | paper_version | url | licence_status | verbatim_ok | format |
|---|---|---|---|---|---|---|---|---|---|---|---|
| DU_programowej_2024.pdf | Rozporządzenie MEN z 28.06.2024, Dz.U. 2024 poz. 1019 | MEN / ISAP | PODSTAWA_PROGRAMOWA | n/a | both | n/a | n/a | https://isap.sejm.gov.pl/isap.nsf/download.xsp/WDU20240001019/O/D20241019.pdf | MATERIAL_URZEDOWY | true | pdf |
| Informator_EM2024_matematyka_pp.pdf | Informator o egzaminie maturalnym z matematyki, poziom podstawowy | CKE | OFFICIAL_CKE | 2023+ | podstawowy | 100 | n/a | https://cke.gov.pl/images/_EGZAMIN_MATURALNY_OD_2023/Informatory/2024/Informator_EM2024_matematyka_pp.pdf | CKE_UNSPECIFIED | false | pdf |
| Informator_EM2024_matematyka_pp_660.docx | Informator o egzaminie maturalnym z matematyki, poziom podstawowy, czarnodruk | CKE | OFFICIAL_CKE | 2023+ | podstawowy | 660 | n/a | https://cke.gov.pl/images/_EGZAMIN_MATURALNY_OD_2023/Informatory/2024/Informator_EM2024_matematyka_pp_660.docx | CKE_UNSPECIFIED | false | docx |
| MMAP-P0-100-A-2605-arkusz.pdf | Arkusz maturalny, matematyka, poziom podstawowy, maj 2026, wersja A | CKE | EXAM | 2605 | podstawowy | 100 | A | https://cke.gov.pl/images/_EGZAMIN_MATURALNY_OD_2023/Arkusze_egzaminacyjne/2026/Matematyka/poziom_podstawowy/MMAP-P0-100-A-2605-arkusz.pdf | CKE_UNSPECIFIED | false | pdf |
| MMAP-P0-100-2605-zasady.pdf | Zasady oceniania rozwiązań zadań, matematyka, poziom podstawowy, maj 2026 | CKE | MARKING_SCHEME | 2605 | podstawowy | 100 | n/a | https://cke.gov.pl/images/_EGZAMIN_MATURALNY_OD_2023/Arkusze_egzaminacyjne/2026/Matematyka/poziom_podstawowy/MMAP-P0-100-2605-zasady.pdf | CKE_UNSPECIFIED | true | pdf |
| wybrane_wzory_matematyczne_EM2023.pdf | Wybrane wzory matematyczne | CKE | FORMULA_SHEET | 2023+ | both | n/a | n/a | https://cke.gov.pl/images/_EGZAMIN_MATURALNY_OD_2023/Informatory/wybrane_wzory_matematyczne_EM2023.pdf | CKE_UNSPECIFIED | true | pdf |
| MMAP-P0-660-A-2605-arkusz.docx | Arkusz maturalny, matematyka PP, maj 2026, wersja A, czarnodruk | CKE | EXAM | 2605 | podstawowy | 660 | A | https://cke.gov.pl/images/_EGZAMIN_MATURALNY_OD_2023/Arkusze_egzaminacyjne/2026/Matematyka/poziom_podstawowy/MMAP-P0-660-A-2605-arkusz.docx | CKE_UNSPECIFIED | false | docx |
| matematyka.pdf | Podstawa programowa kształcenia ogólnego z komentarzem, matematyka (SUPERSEDED — edycja przed nowelizacją z 28.06.2024) | CKE | OTHER | n/a | both | n/a | n/a | https://cke.gov.pl/images/_EGZAMIN_MATURALNY_OD_2015/Formula_2023/podstawa_programowa/matematyka.pdf | CKE_UNSPECIFIED | false | pdf |