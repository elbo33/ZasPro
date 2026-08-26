> Compiled 26 Aug 2026. CKE URLs were harvested from OKE Wrocław's live
> index pages, not fetched directly. Page counts, file sizes and text-layer
> status are unverified. See M0.1 in SPEC.md.

# Resource Dossier: Milestones M0 and M1

Compiled 26 August 2026. Every URL below came from a page I actually retrieved, not from memory.

**One caveat that affects the whole of Part A.** `cke.gov.pl` blocks automated fetching (robots), so I could not open the PDFs themselves. Every CKE URL here was harvested from the live link lists on OKE Wrocław's official pages, which I did retrieve in full. That makes the URLs authentic rather than reconstructed, but it means I cannot report verified page counts, byte sizes, or text-layer status. Wherever a field says "unverified" that is exactly what it means. A one-liner to close that gap is at the end of Part A.

---

## PART A: Official Polish Matura documents

### A0. Which document is actually authoritative right now

This has changed twice since 2022, and the answer is different from what most secondary sites still say.

| period | legal basis for what the exam tests |
|---|---|
| 2023 and 2024 | `wymagania egzaminacyjne`, a reduced set defined by regulation. Formuła 2023: Rozporządzenie MEN i N z 10 czerwca 2022 (Dz.U. 2022 poz. 1246). Formuła 2015: Rozporządzenie z 1 sierpnia 2022 (Dz.U. 2022 poz. 1698). |
| 2025 onward (so 2026 and 2027) | Back to the full `podstawa programowa`. CKE states plainly that from 2025 exam tasks test the 2018 core curriculum as amended in 2024. |

So: **the `wymagania egzaminacyjne` are dead for your purposes.** Do not seed the curriculum tree from them. The authoritative source for M1 is the 2024 `podstawa programowa` (Dz.U. 2024 poz. 1019), and the `informator` is the authoritative description of *how the exam is built* (task types, scoring principles, arkusz structure), not of *what content is examinable*.

Both formulas remain live for 2026 and 2027. Formuła 2015 is being wound down on a staggered schedule (3-year LO graduates through 2026/2027, 4-year technikum through 2027/2028, branżowa II stopnia through 2028/2029). If your product targets current school leavers, Formuła 2023 is the only tree you need. Formuła 2015 papers are still useful as extra exercise stock, with a provenance flag.

<cite index="15-1">CKE's own framing is that the informatory are the single reliable source of information about the Formuła 2023 exam.</cite> Treat that as a claim by the publisher, not as a legal statement about scope.

### A1. Curriculum and requirements

| title | URL | publisher | year / session | level | format | size | terms | confidence |
|---|---|---|---|---|---|---|---|---|
| Rozporządzenie Ministra Edukacji z 28 czerwca 2024 r. zmieniające rozporządzenie w sprawie podstawy programowej kształcenia ogólnego dla liceum ogólnokształcącego, technikum oraz branżowej szkoły II stopnia (Dz.U. 2024 poz. 1019) | https://isap.sejm.gov.pl/isap.nsf/download.xsp/WDU20240001019/O/D20241019.pdf | MEN, via ISAP (Sejm) | in force from 1 Sept 2024; governs the 2025+ exams | both (rozszerzony defined as podstawowy plus additions) | born-digital PDF, text layer near-certain (ISAP output), unverified | large, whole-curriculum annex, unverified | Dz.U. text is `materiał urzędowy`, outside copyright under art. 4 pr. aut. Safe to ingest. | High |
| Same regulation, CKE's own mirror | https://cke.gov.pl/images/_EGZAMIN_MATURALNY_OD_2023/podstawa_programowa/DU_programowej_2024.pdf | CKE | as above | both | unverified | unverified | see A5 | High |
| Informator o egzaminie maturalnym z matematyki od roku szkolnego 2022/2023, poziom podstawowy | https://cke.gov.pl/images/_EGZAMIN_MATURALNY_OD_2023/Informatory/2024/Informator_EM2024_matematyka_pp.pdf | CKE | Formuła 2023, current | podstawowy | unverified | unverified | see A5 | High |
| Informator ... z matematyki, poziom rozszerzony | https://cke.gov.pl/images/_EGZAMIN_MATURALNY_OD_2023/Informatory/2024/Informator_EM2024_matematyka_pr.pdf | CKE | Formuła 2023, current | rozszerzony | unverified | unverified | see A5 | High |
| Informator, część ogólna, wersja 2026 (file dated 2025-08-20) | http://cke.gov.pl/images/_EGZAMIN_MATURALNY_OD_2023/Informatory/2025/20250820%20Informator%20Cz%C4%99%C5%9B%C4%87%20og%C3%B3lna%20EM23%20wer_2026.pdf | CKE | from 2025, revised Aug 2025 | n/a | unverified | unverified | see A5 | High |
| Informator maths, accessible Word versions (`czarnodruk`) PP / PR | https://cke.gov.pl/images/_EGZAMIN_MATURALNY_OD_2023/Informatory/2024/Informator_EM2024_matematyka_pp_660.docx and .../Informator_EM2024_matematyka_pr_660.docx | CKE | as above | both | DOCX, native text | unverified | see A5 | High |
| Wymagania egzaminacyjne na egzaminie maturalnym w 2023 r. (superseded) | https://www.gov.pl/web/edukacja/wymagania-egzaminacyjne-obowiazujace-na-egzaminie-maturalnym-w-roku-2023-i-2024 | MEN | 2023 and 2024 only | both | landing page with PDF attachment, ~2.48 MB | unverified | gov.pl | High that it is superseded |
| Informatory index page (all subjects, Formuła 2023) | https://cke.gov.pl/egzamin-maturalny/egzamin-maturalny-w-formule-2023/informatory/ | CKE | current | n/a | HTML | n/a | n/a | High |
| Same index, mirrored by OKE Wrocław (this one is fetchable by bots) | https://oke.wroc.pl/egzamin-maturalny/formula-2023/informatory-5/ | OKE Wrocław | current | n/a | HTML | n/a | n/a | High |

The `czarnodruk` DOCX files are the single most useful thing in this table and I would not have flagged them if you had not said `format` matters more than it looks. See Surprises.

### A2. Formula sheet

| title | URL | publisher | year | level | format | size | terms | confidence |
|---|---|---|---|---|---|---|---|---|
| Wybrane wzory matematyczne | https://cke.gov.pl/images/_EGZAMIN_MATURALNY_OD_2023/Informatory/wybrane_wzory_matematyczne_EM2023.pdf | CKE | Formuła 2023, current edition, same file linked from both PP and PR informatory | both, single shared booklet | unverified | unverified | see A5 | High |
| Wybrane wzory matematyczne dla osób niewidomych (ZIP) | http://cke.gov.pl/images/_EGZAMIN_MATURALNY_OD_2023/Informatory/tablice_mat.zip | CKE | current | both | ZIP, braille/DBT source | unverified | see A5 | Medium (contents unverified) |
| Formuła 2015 formula sheet and tables | https://oke.wroc.pl/egzamin-maturalny/formula-2015/wzory-materialy/ | OKE Wrocław / CKE | Formuła 2015 | both | landing page | n/a | see A5 | Medium |

The single shared booklet across both levels is worth noting for M1: your `formulas` table does not need a level discriminator sourced from this document. <cite index="27-1">The formula card is supplied by the school at the exam, alongside a ruler, compass and simple calculator.</cite>

### A3. Past papers and marking schemes

CKE's file naming is fully systematic, which makes crawling trivial. Pattern:

```
https://cke.gov.pl/images/_EGZAMIN_MATURALNY_OD_2023/Arkusze_egzaminacyjne/
  {YEAR}/Matematyka/{poziom_podstawowy|poziom_rozszerzony}/
  MMAP-{P0|R0}-{100|200|660}-{A|B}-{YYMM}-{arkusz|karta}.pdf
  MMAP-{P0|R0}-{100|660}-{YYMM}-zasady.pdf
```

`MMAP` is the maths subject code. `P0`/`R0` is the level. `100` is the standard version, `200` the autism/Asperger adaptation, `660` the blind adaptation (DOCX plus `.dxb`), `700` the deaf adaptation. `A`/`B` are parallel versions. `YYMM` is the session, so `2605` is May 2026. `-zasady` is the marking scheme, and it is shared across versions within a level.

Verified concrete example, maj 2026 (all harvested from OKE Wrocław's 2026 arkusze post):

| item | URL |
|---|---|
| PP wersja A, arkusz | https://cke.gov.pl/images/_EGZAMIN_MATURALNY_OD_2023/Arkusze_egzaminacyjne/2026/Matematyka/poziom_podstawowy/MMAP-P0-100-A-2605-arkusz.pdf |
| PP wersja B, arkusz | .../poziom_podstawowy/MMAP-P0-100-B-2605-arkusz.pdf |
| PP zasady oceniania | .../poziom_podstawowy/MMAP-P0-100-2605-zasady.pdf |
| PP czarnodruk (DOCX) | .../poziom_podstawowy/MMAP-P0-660-A-2605-arkusz.docx |
| PR arkusz | .../poziom_rozszerzony/MMAP-R0-100-A-2605-arkusz.pdf |
| PR zasady oceniania | .../poziom_rozszerzony/MMAP-R0-100-2605-zasady.pdf |

**Sessions that exist for Formuła 2023.** From OKE Wrocław's arkusze index, which is the cleanest inventory I found:

| session | type | landing page |
|---|---|---|
| marzec 2022 | arkusze pokazowe | https://cke.gov.pl/egzamin-maturalny/egzamin-maturalny-w-formule-2023/materialy-dodatkowe/arkusze-pokazowe-marzec-2022/ |
| wrzesień 2022 | test diagnostyczny | https://cke.gov.pl/egzamin-maturalny/egzamin-maturalny-w-formule-2023/materialy-dodatkowe/arkusze-diagnostyczne-wrzesien-2022/ |
| grudzień 2022 | test diagnostyczny | https://oke.wroc.pl/aktualnosci/egzamin-maturalny-215/ |
| maj 2023 | main | https://oke.wroc.pl/arkusze-egzamin-maturalny-2023/ |
| grudzień 2023 | test diagnostyczny | https://cke.gov.pl/egzamin-maturalny/egzamin-maturalny-w-formule-2023/materialy-dodatkowe/arkusze-diagnostyczne-grudzien-2023/ |
| maj 2024 | main | https://oke.wroc.pl/arkusze-egzaminacyjne-maj-2024-formula-2023/ |
| grudzień 2024 | test diagnostyczny | https://cke.gov.pl/egzamin-maturalny/egzamin-maturalny-w-formule-2023/materialy-dodatkowe/arkusze-diagnostyczne-grudzien-2024/ |
| maj 2025 | main | https://oke.wroc.pl/aktualnosci/egzamin-maturalny-arkusze/ |
| styczeń 2026 | próbny | https://oke.wroc.pl/aktualnosci/arkusze-probny-egzamin-maturalny-2026/ |
| maj 2026 | main | https://oke.wroc.pl/egzamin-maturalny/egzamin-maturalny-2026-arkusze/ |

Index pages: CKE https://cke.gov.pl/egzamin-maturalny/egzamin-maturalny-w-formule-2023/arkusze/ ; OKE Wrocław https://oke.wroc.pl/egzamin-maturalny/formula-2023/arkusze-egzaminacyjne-3/ (bot-fetchable). Formuła 2015 archive: https://oke.wroc.pl/egzamin-maturalny/formula-2015/egzamin-maturalny-arkusze-egzaminacyjne/

**Gaps in this inventory, stated honestly.** OKE Wrocław's Formuła 2023 index lists only the May main sessions. It does not list czerwiec (additional) or sierpień (retake) papers, even though those sessions exist. <cite index="8-1">The 2026 retake written papers were sat on 24 August 2026.</cite> Those papers are published by CKE but under a different session code (`2606`, `2608`) and I could not confirm the exact directory layout for them without fetching CKE directly. Assume they follow the same pattern and verify before relying on it.

For Formuła 2023 you are looking at roughly 10 sessions to date across two levels, so on the order of 40 to 60 maths PDFs including marking schemes and parallel versions. That is a small enough corpus that a hand-audited manifest beats a clever crawler.

### A4. Supplementary official material

| title | URL | publisher | year | format | size | confidence |
|---|---|---|---|---|---|---|
| Komunikat o materiałach i przyborach pomocniczych w 2026 r. | https://cke.gov.pl/images/_EGZAMIN_MATURALNY_OD_2023/komunikaty/2026/komunikaty/20250820%20E8_EM%20Komunikat%20o%20przyborach%202026.pdf | CKE | 2026 | PDF, ~333 kB | High |
| Harmonogram, komunikaty i informacje, rok szkolny 2025/2026 (hub) | https://bip.cke.gov.pl/artykul/285/1952/harmonogram-komunikaty-i-informacje | CKE BIP | 2025/26 | HTML index with sizes | High |
| Harmonogram, komunikaty i informacje, rok szkolny 2026/2027 (hub) | https://bip.cke.gov.pl/artykul/286/1999/harmonogram-komunikaty-i-informacje | CKE BIP | 2026/27 | HTML index | High |
| Komunikat o harmonogramie egzaminów w 2027 r. | via the 2026/2027 hub above; <cite index="21-1">listed there as PDF, 394 kB</cite> | CKE | published 20 Aug 2026 | PDF | High |
| Komunikat o materiałach i przyborach pomocniczych w 2027 r. | via the same hub; <cite index="22-1">PDF, 341 kB</cite> | CKE | 2027 | PDF | High |
| Informator index on CKE BIP (has per-file metryczki) | https://bip.cke.gov.pl/artykul/211/1659/egzamin-maturalny-w-formule-2023 | CKE BIP | current | HTML | High |

CKE BIP is the better source for supplementary documents than the main site: it publishes file sizes and change metadata (`metryczka`) per attachment, which is exactly what an ingestion pipeline wants for change detection.

Note for M1 scope: the "zasady oceniania z komentarzami" and worked example solutions you might want for a `misconceptions` table live inside the informatory, not in a separate publication. <cite index="15-1">The informatory contain task-type descriptions, arkusz descriptions, marking principles with commentary, and worked examples.</cite>

### A5. Terms of use

CKE does not publish an explicit reuse licence next to the arkusze. The relevant frame, and I am inferring here rather than quoting a CKE statement:

- Regulations published in Dziennik Ustaw (the podstawa programowa) are `materiały urzędowe` and fall outside copyright under art. 4 of the Polish copyright act. Unambiguously safe.
- Exam papers are argued to be `dokumenty urzędowe` on the same basis, but commentators note that the art. 4 exclusion does not amount to unlimited freedom to reproduce, and that other bodies of law can still constrain it. This is genuinely contested rather than settled.
- Individual exam papers frequently embed third-party material (literary excerpts, photographs, diagrams) whose rights sit with someone other than CKE. Maths papers are the least exposed subject here, but not zero exposure on figures.
- CKE is also a `podmiot zobowiązany` under the open data / public-sector information reuse regime, so a formal reuse request is available if you ever need certainty.

**My recommendation:** ingest freely for internal knowledge-base construction. Before you publish derived content at scale, get an actual Polish IP opinion on reproducing arkusz task text verbatim, and design the schema now so that every exercise row carries a `source_licence` and `verbatim_ok` flag. Retrofitting that later is painful. I am not a lawyer and this is not legal advice.

### A6. Closing the format gap

Since I could not open the PDFs, run this before M0 planning. It answers the text-layer question for the whole corpus in one pass:

```bash
for f in corpus/*.pdf; do
  chars=$(pdftotext "$f" - 2>/dev/null | tr -d '[:space:]' | wc -c)
  pages=$(pdfinfo "$f" | awk '/^Pages:/{print $2}')
  echo "$f pages=$pages chars_per_page=$((chars / (pages>0?pages:1)))"
done
```

Under roughly 100 characters per page means image-only. My expectation, stated as inference and not fact: everything from Formuła 2023 (2022 onward) is born-digital with a real text layer, because CKE has been typesetting these in Word/InDesign for years and ships DOCX siblings. Formuła 2015 papers from the mid-2010s are probably also born-digital. Anything from before roughly 2010, if you go that far back, is more likely to be scanned.

---

## PART B: PDF and mathematics extraction

### B1. General-purpose Python PDF extraction

| tool | what it is good at | where it fails | maintained | licence | local/API | cost |
|---|---|---|---|---|---|---|
| **PyMuPDF / pymupdf4llm** | Fastest text and layout extraction with character-level coordinates. `pymupdf4llm` emits Markdown directly. The right tool for the anchor-text layer of a hybrid pipeline. | No maths semantics at all. Reading order on multi-column pages is heuristic. | Yes | AGPL-3.0, commercial licence available. This matters if you ever ship the pipeline. | Local | Free / paid licence |
| **pdfplumber** | Best-in-class access to per-character boxes, sizes, font names. If you want to detect superscripts geometrically, this is the tool. | Slow on large corpora. No table or maths intelligence beyond what you write. | Yes | MIT | Local | Free |
| **pypdf** | Metadata, page manipulation, splitting. | Weakest text extraction of the three. | Yes | BSD | Local | Free |
| **poppler / pdftotext -layout** | The fastest sanity check for whether a text layer exists at all. Use it in the audit above. | Nothing structural. | Yes | GPL | Local | Free |

For your specific problem, pdfplumber's character geometry is more valuable than it looks. Exercise numbering in Polish arkusze is visually distinctive (bold, left-aligned, `Zadanie 12. (0-2)` pattern), and a geometric rule over pdfplumber output will beat any model at finding problem boundaries. See B6.

### B2. Model-based document parsers

| tool | strengths | weaknesses | maintained | licence | local/API |
|---|---|---|---|---|---|
| **MinerU** (v2.5) | Pipeline architecture with DocLayout-YOLO for layout, dedicated formula and table models. Strong on layout detection specifically. | Weaker end-to-end than the newer VLMs. <cite index="74-1">Scored 61.5 overall and 47.4 on the Old Scans Math slice of olmOCR-Bench.</cite> | Very active | AGPL-3.0 | Local (GPU) |
| **Marker** | Practical, well-engineered PDF-to-Markdown, optional LLM assist for inline maths and cross-page tables. Good default open-source choice. | <cite index="74-1">70.1 overall on olmOCR-Bench, 57.9 on old-scan maths.</cite> | Very active | GPL-3.0 for code, model licences vary | Local |
| **Docling** (IBM) | Cleanest structured output object model, best hierarchy preservation, easy to integrate. A 2025 comparison on Portuguese administrative documents found <cite index="70-1">Docling with hierarchical splitting and image descriptions reached the highest automated accuracy at 94.1%, against 86.9% for a naive PDF loader and 97.1% for hand-curated Markdown.</cite> | Maths is not its strong suit relative to the maths-specialised models. | Very active | MIT | Local |
| **olmOCR / olmOCR 2** (AI2) | VLM-based, purpose-built for PDF linearisation, and the only one in this list with a rigorous public eval methodology. <cite index="71-1">olmOCR-2 scores 82.4 on olmOCR-Bench at 1.78 pages/sec.</cite> | Needs a GPU. Output is linearised text, so you rebuild structure downstream. | Very active | Apache 2.0 | Local (GPU) |
| **dots.ocr, PaddleOCR-VL, DeepSeek-OCR, Chandra, Nanonets-OCR2** | The October 2025 cohort. <cite index="71-1">Chandra leads at 83.1 on olmOCR-Bench; dots.ocr and PaddleOCR-VL land around 79 to 80; DeepSeek-OCR trades accuracy for speed at 75.7 and 4.65 pages/sec.</cite> | Rapidly churning. Licences vary and some are restrictive. | Very active | Varies | Local (GPU) |
| **Surya** | Good layout and reading-order detection as a component. | <cite index="72-1">Code is GPL-3.0 but the model weights sit under a licence that is free only for research and companies under $2M revenue.</cite> | Active | Split, see above | Local |
| **Nougat** (Meta) | Historically the reference academic-PDF-to-markup model. | Effectively superseded. Do not start here in 2026. | Stale | MIT | Local |

### B3. Formula-to-LaTeX specialists

- **UniMERNet** is the strongest open formula recogniser in the OmniDocBench evaluation. <cite index="67-1">GPT-4o, Mathpix and UniMERNet took the top three formula-recognition scores at 86.8%, 86.6% and 85.0% respectively.</cite>
- **pix2tex (LaTeX-OCR)** and **texify** are the lightweight options. Fine for a clean isolated display equation, poor on anything with surrounding context. MIT/GPL respectively, local, free.
- **Pix2Text** is evaluated in OmniDocBench as a full parser rather than just a formula model; it sits mid-pack.

A note that will save you time: raw edit distance is a bad metric for formula accuracy, and the tooling now reflects that. <cite index="73-1">The olmOCR 2 authors show cases where the model whose output is more textually dissimilar to the reference LaTeX nonetheless renders correctly, and cite CDM as further exploration of edit distance's limitations for maths.</cite> If you build your own M0 eval, compare rendered output, not strings.

### B4. Commercial maths OCR

**Mathpix** remains the reference commercial option and the only one built around maths first.

- Convert API: <cite index="81-1">$0.005 per page for the first million pages of `v3/pdf`, dropping to $0.0035 per page beyond a million.</cite> Images are billed separately at around $0.002. <cite index="82-1">A one-time non-refundable setup fee activates API keys, with a $29 credit applied for testing.</cite>
- Snip Pro is $4.99 per month with a free tier, which is the cheapest way to eyeball quality on ten real arkusz pages before writing any code.
- Practical arithmetic for you: 60 maths PDFs at roughly 20 pages each is about 1,200 pages, so under $10 to run the entire Formuła 2023 corpus through Mathpix once. The cost objection to commercial OCR does not apply at your scale.

Azure Document Intelligence, AWS Textract and Google Document AI are all viable for text and layout but none is maths-first, and <cite index="71-1">basic text extraction runs around $1,500 per million pages with structured extraction climbing to $10,000 to $50,000 per million.</cite>

### B5. Page-image plus VLM with structured output

This is the approach I would bet on for your corpus, and B5 is where Parts B and C meet: the VLM emits JSON, Pydantic v2 validates it, and invalid output is retried. Two properties matter for exam papers specifically:

1. You can put the schema in the prompt, so `exercise_number`, `points_available`, `subtasks[]` and `statement_latex` come back as fields rather than being recovered from prose.
2. You can pass the pdfplumber text layer alongside the image as anchor text, which is precisely the trick olmOCR uses. <cite index="128-1">olmOCR's input is a rasterised page at a maximum 1024 pixels on the longest edge plus roughly 1,800 tokens of anchor text.</cite>

The trade-off is cost per page and non-determinism. Both are manageable at 1,200 pages.

### B6. Your six questions, answered directly

**1. Realistic failure rate of plain text-layer extraction on typeset maths.**

I found no published figure for "percentage of equations correctly recovered by pdftotext", and I do not think one exists, because the failure is not probabilistic but structural. Plain text-layer extraction recovers the *glyphs* and *positions*; it does not recover the *relations* between them, and maths is entirely relations. Concretely, in decreasing order of severity:

- **Fractions**: catastrophic. Numerator and denominator are separate text runs at different y-positions. `pdftotext` typically emits them on separate lines or interleaved with adjacent text. There is no vinculum character to key on, only a drawn line.
- **Radicals**: catastrophic for the same reason. The radicand's extent is defined by the drawn overbar, which is a graphics operator, not text.
- **Matrices**: catastrophic. Delimiters are usually drawn or built from glyph pieces; cell structure is pure geometry.
- **Subscripts and superscripts**: recoverable but only geometrically. The characters come through in the correct sequence, with no marker distinguishing `x2` (x squared) from `x2` (x sub 2) from literal `x2`. pdfplumber's per-character `size` and `top` fields give you enough to reconstruct this with a threshold rule, which is why pdfplumber earns its place in B1.
- **Inline versus display**: recoverable heuristically. Display equations are typically centred with distinct vertical spacing. Inline maths is the harder case and the one the benchmarks under-weight.
- **Sequence order**: the sleeper problem. Text runs come out in PDF content-stream order, which for typeset maths is often authoring order rather than reading order.

Rendered-page benchmarks are the closest available proxy and they are sobering: the best models in the field cluster in the low 80s, and <cite index="76-1">LlamaIndex's assessment is that document parsing is not close to being solved even by frontier models.</cite> There is a 2026 benchmark whose title makes the point, "How Far Is Document Parsing from Solved? PureDocBench" (arXiv 2605.07492).

**2. Polish diacritics and Polish-language documents.**

No Polish-specific published benchmark exists that I could find. That is itself a finding. What I can tell you is the mechanism, which is well documented and language-agnostic:

Polish diacritics (ą ć ę ł ń ó ś ź ż) live in Latin Extended-A, U+0100 to U+017F, outside WinAnsi. Extraction fidelity therefore depends entirely on the PDF's `ToUnicode` CMap being present and correct for the embedded subset font. When it is not, you get silent, systematic corruption rather than an error: <cite index="88-1">a documented 2026 case shows Polish diacritics being mapped to wrong code points and emerging as garbled ASCII.</cite> The general form is well known: <cite index="94-1">if a font uses custom encoding and the ToUnicode map is absent from the font resource, accurate text extraction is impossible.</cite>

Two practical consequences. First, add a Polish diacritic sanity assertion to your M0 harness: extract, then check the ratio of diacritics to total letters is plausible for Polish prose (roughly 8 to 12 percent). A near-zero ratio means silent corruption, not a document without diacritics. Second, `ł` (U+0142) is the canonical canary because it has no unaccented visual fallback and is extremely common.

For OCR paths, Tesseract needs `-l pol` explicitly. Modern VLMs handle Polish well but I have no benchmark to cite, and the OmniDocBench language coverage is English and Chinese, so **treat all published scores as not directly transferable to your corpus.**

**3. Published benchmarks you can use instead of building your own.**

Yes, three good ones, all recent:

- **OmniDocBench**, CVPR 2025, arXiv 2412.07626, https://github.com/opendatalab/OmniDocBench. <cite index="64-1">1,651 PDF pages across 10 document types, 5 layout types and 5 language types, with 28 block-level and 4 span-level annotations including inline formulas and subscripts.</cite> Crucially for you it evaluates formula recognition as a separate task with LaTeX ground truth. Actively updated: <cite index="64-1">the 31 July 2025 refresh added MinerU2-VLM, Marker 1.7.1, PP-StructureV3, Dolphin, Nanonets-OCR-s, OCRFlux-3B and Qwen2.5-VL-7B.</cite>
- **olmOCR-Bench**, arXiv 2510.19817, https://arxiv.org/html/2510.19817v1. Binary pass/fail unit tests rather than edit distance, with a dedicated "Old Scans Math" slice. Methodologically the best of the three. Read LlamaIndex's critique alongside it: https://www.llamaindex.ai/blog/olmocr-bench-review-insights-and-pitfalls-on-an-ocr-benchmark
- **PureDocBench**, arXiv 2605.07492 (2026). Source-traceable, splits clean / degraded / real-world settings. The most recent thing I found, and the "real-world" split is closer to your use case than the arXiv-paper splits that dominate the others.
- **READoc**, ACL 2025 Findings, is worth knowing about because it frames document extraction as structured extraction rather than text dumping, which is closer to what M1 needs.

**4. DPI and preprocessing for the page-image route.**

Two different answers depending on which path you take, and conflating them is a common mistake.

- **Classical OCR (Tesseract):** 300 DPI is the long-standing convention. <cite index="124-1">OCRmyPDF's documentation uses a 300 DPI 8.5x11 inch page as its reference unit, 8.4 megapixels.</cite> Preprocessing that matters: deskew, rotation correction, background removal. OCRmyPDF exposes all of these via `--deskew`, `--rotate-pages`, `--clean` and `--oversample`, and its cookbook cautions that cleaning can remove desirable content on poor scans. For born-digital CKE PDFs none of this applies, because there is nothing to deskew.
- **VLM path:** lower than you would expect, and capped by pixel dimension rather than DPI. <cite index="123-1">olmOCR renders pages to a maximum 1024 pixels on the longest edge.</cite> A 2026 practitioner comparison used <cite index="122-1">200 DPI capped at 1540px on the longest dimension, and stresses that normalising this across methods is critical, because otherwise you are comparing preprocessing pipelines rather than models.</cite> That warning is the single most useful thing to internalise for M0: **fix your rendering parameters first, then compare extractors.**

**5. What people converge on for exam papers and textbooks specifically.**

Honest answer: I found no published study on exam papers as a document class. Research papers dominate every benchmark, and the reason matters, because arXiv sources give free LaTeX ground truth at scale. Exam papers have no such corpus.

What I can offer is inference from the structural differences, flagged as inference:

Exam papers are *easier* than research papers in the ways that dominate the benchmarks (single column, no citations, no floats, no cross-page tables, consistent house typography across sessions) and *harder* in one way the benchmarks do not measure at all (the unit of meaning is the numbered exercise, not the page or the paragraph). A tool that scores 83 on olmOCR-Bench may still be useless to you if it dissolves exercise boundaries.

The pattern that seems to actually work, and which I would propose for M0: a **hybrid, not a single tool.** Structure from geometry (pdfplumber, deterministic, reproducible), maths from a specialist (Mathpix or a VLM, on cropped regions), and reconciliation in code. The consistency of CKE's typography across ten sessions is an asset that no general-purpose tool will exploit but a fifty-line rule set will.

**6. Anything that reliably preserves exercise numbering and problem boundaries.**

No, and I want to be direct about this because you flagged it as your priority. Nothing in the current landscape targets it. Document parsers optimise for text fidelity and reading order; formula tools operate below the exercise level; VLMs will produce boundaries if you ask, but "reliably" is not a word the evidence supports.

The good news is that this is the easiest part of your problem to solve yourself, precisely because it does not need a model. CKE arkusze number exercises with a rigid, machine-friendly convention (`Zadanie N.` and `Zadanie N. (0-M)` for point values, with subtasks as `N.1`, or `a)` / `b)`). A regex over pdfplumber output, constrained by font weight and x-position and validated against the marking scheme's own exercise list, will get you near-perfect boundaries.

That last clause is the trick worth stealing: **the `-zasady` marking scheme is an independent enumeration of every exercise in the paper, with point values.** Cross-validating the arkusz against its own marking scheme gives you a free correctness check on boundary detection, and it flags any exercise you dropped. I would make that check a hard gate in M0.

---

## PART C: Technical references for M1

### SQLAlchemy 2.x typed ORM

- **ORM Quick Start**, https://docs.sqlalchemy.org/en/20/orm/quickstart.html. The shortest path to the modern idiom. <cite index="99-1">Column types derive from the Python type inside the `Mapped` annotation, and nullability derives from whether `Optional[]` is used.</cite>
- **Table Configuration with Declarative**, https://docs.sqlalchemy.org/en/20/orm/declarative_tables.html. The one to read properly. Covers `type_annotation_map` and PEP 593 `Annotated` reuse, which is how you define a `curriculum_id` or `slug` type once and reuse it across every model. For a schema with as many tables as yours that is the difference between clean and repetitive.
- Secondary: **What's New in SQLAlchemy 2.0**, https://docs.sqlalchemy.org/en/21/changelog/whatsnew_20.html, specifically the dataclass integration section. <cite index="100-1">PEP 681 support lets mapped classes gain a real `__init__` with positional arguments and customisable defaults.</cite> Useful if you want your ORM models to double as the objects your Pydantic layer hands off to.
- **Version note:** 2.1 documentation is now live at `/en/21/`. Pin explicitly in `pyproject.toml` and read the docs for the version you pinned.

### Alembic

- **Alembic documentation**, https://alembic.sqlalchemy.org/en/latest/ (canonical entry point; I did not independently fetch this one, so verify the exact deep links yourself).

On batching migrations by feature, which is what you actually asked: this is a workflow question rather than an Alembic feature, and the pattern that holds up is one linear revision chain with one revision per logical feature, not per model change. Squash the noise during development by deleting and regenerating revisions freely before anything is applied to a shared database, then treat every revision as immutable once it has been. Give revisions meaningful slugs (`--rev-id 0007_curriculum_tree` rather than a hash) because in eighteen months the migration log is the only honest history of your schema. Branching and merge points exist in Alembic but are a solution to multiple teams, and you do not have that problem.

One M1-specific trap, worth stating because it will bite you: **never put a pgvector IVFFlat index in a migration.** See the pgvector entry below.

### Hierarchical curriculum trees in PostgreSQL

- **ltree**, https://www.postgresql.org/docs/current/ltree.html (canonical; verify the exact anchor).
- **WITH Queries (CTEs)**, https://www.postgresql.org/docs/current/queries-with.html. Covers recursive traversal and the `SEARCH` and `CYCLE` clauses.
- Secondary: **Cybertec, "Speeding up recursive queries and hierarchical data"**, https://www.cybertec-postgresql.com/en/postgresql-speeding-up-recursive-queries-and-hierarchic-data/. The clearest practical comparison I found, and it flags the ltree gotchas nobody mentions: <cite index="109-1">ltree holds labels rather than arbitrary strings, and you can append to a path containing an empty string but not to a NULL.</cite> That second one will silently produce wrong trees if you seed from a CSV with blanks.

**My read on the trade-off for your case.** A Matura curriculum tree is small (a few hundred nodes), shallow (roughly `dział > temat > podtemat > wymaganie`), and almost entirely read-only after seeding. That profile makes the usual performance argument for materialized paths or ltree irrelevant. Use an **adjacency list** (`parent_id` self-FK) as the source of truth, because it is the only representation where a reparenting operation is a single-row update and cannot produce an inconsistent state. Add a generated materialized path column *if and when* you find yourself writing the same recursive CTE for the fifth time. Reach for ltree only if you end up wanting its pattern-matching query operators, which is a different reason from performance. Adding ltree later is a migration; committing to it early and regretting it is a rewrite.

### Cycle detection in a prerequisite graph

- **WITH Queries**, https://www.postgresql.org/docs/current/queries-with.html, same page as above. <cite index="107-1">The `CYCLE` clause takes the columns to track, a column name that flags whether a cycle was detected, and a column that tracks the path.</cite> Available since PostgreSQL 14. <cite index="111-1">The syntax is `CYCLE id SET is_cycle USING cycle_path`, and recursion stops automatically on any detected loop.</cite>
- Secondary: **sqlfordevs, "Cycle Detection for Recursive Search in Hierarchical Trees"**, https://sqlfordevs.com/cycle-detection-recursive-query. Two screens long, exactly the right length for this.

Design note. Your prerequisite graph is a DAG over concepts and is a genuinely different structure from the curriculum tree, even though both are "hierarchical". Keep them in separate tables. Enforce acyclicity with a `CYCLE`-based check at write time, not by trusting the seeding process, because prerequisite edges are the thing you will most often add by hand or by LLM inference and therefore the thing most likely to acquire a loop.

### Pydantic v2 for validating model output

- **Pydantic documentation**, https://docs.pydantic.dev/latest/ (canonical; verify).
- The pattern you want is well established: define the schema as a `BaseModel`, emit `model_json_schema()` into the prompt or into the API's structured-output parameter, then `model_validate_json()` the response with retry on `ValidationError`. Feed the validation error text back into the retry prompt, since that is what makes the retry converge instead of repeating.
- For your case specifically, put the domain constraints in the validators rather than in the prompt. `points_available` between 0 and 6, `exercise_number` monotonically increasing within a paper, `subtask_count` matching the marking scheme. Prompts are suggestions; validators are guarantees, and the difference shows up at 1,200 pages.
- Worth knowing: **Instructor** (https://github.com/567-labs/instructor) wraps exactly this loop if you would rather not write it. Given your preference for iterating rather than over-engineering up front, I would write the twenty-line version first and only reach for the library if it stops being twenty lines.

### pgvector (later reference only)

- **pgvector**, https://github.com/pgvector/pgvector. Canonical, and the README is genuinely the best documentation. <cite index="118-1">By default pgvector does exact nearest-neighbour search with perfect recall; an approximate index trades recall for speed, HNSW has better query performance than IVFFlat but slower builds and more memory, and an HNSW index can be created on an empty table because there is no training step.</cite>
- Secondary: **BigDataBoutique, "HNSW vs IVFFlat"**, https://bigdataboutique.com/blog/hnsw-vs-ivfflat-how-to-choose-the-right-vector-index (May 2026). <cite index="116-1">HNSW is the 2026 default for most production workloads; IVFFlat earns its place when the dataset is very large, mostly static, and memory or build time dominates. pgvector 0.8.2 (February 2026) is current and supports HNSW, IVFFlat, halfvec, sparsevec and binary quantization.</cite>

**When it is not worth adding.** Almost certainly not during M1, and possibly never. Your corpus is on the order of thousands of concepts and exercises. <cite index="121-1">Exact search with no index is the correct choice below roughly 50,000 rows</cite>, and adding an approximate index at your scale buys nothing while introducing a silent correctness risk. Concretely, the failure mode: <cite index="121-1">IVFFlat index quality is fixed at build time by k-means over whatever data exists when `CREATE INDEX` runs</cite>, so an IVFFlat index created in an Alembic migration against an empty table is permanently broken and degrades recall silently forever. <cite index="119-1">This is a documented, commonly-encountered failure that takes weeks to diagnose because nothing errors; queries just quietly return the wrong neighbours.</cite> If you eventually need vector search, use HNSW and build it in a post-load script, not a migration.

---

## Gaps

1. **Verified file properties for every Part A document.** `cke.gov.pl` disallows automated access, so I could not confirm page counts, byte sizes, or text-layer presence for any CKE-hosted PDF. Reason: robots policy, not a broken link. The audit script in A6 closes this in about a minute.
2. **Czerwiec and sierpień session papers.** OKE Wrocław's Formuła 2023 index lists only May main sessions. The additional and retake papers exist and are published, but I could not confirm their directory layout. Reason: the regional boards curate their index pages selectively; CKE's own arkusze page is the complete list and is the page I could not fetch.
3. **A published Polish-language extraction benchmark.** None exists that I could find. Every major benchmark is English and Chinese, occasionally with a broader language axis that does not break out Polish. This is a real gap in the literature and not a gap in my searching.
4. **Any study of exam papers as a document class.** Same story. arXiv papers dominate because they come with free LaTeX ground truth.
5. **An explicit CKE reuse licence.** CKE publishes no licence statement next to the arkusze. The legal position has to be assembled from the copyright act and the public-sector-information regime, which is why A5 is hedged.
6. **Alembic, ltree and Pydantic canonical URLs.** I have given the well-known entry points but did not independently fetch these three, unlike everything else in Part C. Flagging that rather than implying a verification I did not do.

## Surprises

1. **CKE publishes DOCX versions of everything.** The `czarnodruk` accessibility files (`_660.docx`) are native Word documents of the informatory and of every exam paper, produced for blind candidates. This is the biggest finding in this dossier. A DOCX has real structure: headings, numbered lists, and in all likelihood OMML equations. If those files carry the maths as OMML, your M0 spike may be answering the wrong question entirely, because you would not need PDF extraction for a meaningful slice of the corpus at all. **Check one of these files before you write a line of M0 code.** Start with `https://cke.gov.pl/images/_EGZAMIN_MATURALNY_OD_2023/Informatory/2024/Informator_EM2024_matematyka_pp_660.docx`, unzip it, and grep `word/document.xml` for `m:oMath`. If it is there, OMML converts to LaTeX cleanly and deterministically, and your extraction problem shrinks by an order of magnitude.
2. **The marking scheme is a free ground-truth index.** Every `-zasady.pdf` independently enumerates the paper's exercises with point values. That is a validation oracle for the boundary detection you said matters most, and it costs nothing to use.
3. **The authoritative requirements document changed under everyone's feet in 2025.** A large fraction of Polish tutoring sites still cite the 2022 `wymagania egzaminacyjne`. If you seed M1 from a secondary source or from an LLM's recollection you will get the wrong tree. Seed from Dz.U. 2024 poz. 1019.
4. **Two parallel versions per paper (A and B) since at least 2026.** Maths PP for maj 2026 has `MMAP-P0-100-A` and `MMAP-P0-100-B`. Your schema needs a version discriminator or you will silently create duplicate exercises that are near-identical but not identical. This is a schema decision, so it belongs in M1, not M0.
5. **Adaptation variants are a fifth axis nobody plans for.** `100` / `200` / `660` / `700` are standard, autism/Asperger, blind, deaf. The `200` variants in particular are content-equivalent but differently typeset. Decide now whether you ingest them.
6. **CKE BIP is better than CKE's main site for pipeline purposes.** It publishes per-file sizes and `metryczka` change metadata, which gives you change detection for free.

## Open questions, decisions needed before M0 starts

1. **Do the `czarnodruk` DOCX files contain OMML maths?** This is the highest-leverage unknown and takes five minutes to resolve. If yes, M0's scope changes fundamentally: the spike becomes "DOCX-first with PDF fallback" rather than "compare PDF extraction methods". I would resolve this before finalising M0's design.
2. **Formuła 2015: in scope or out?** It roughly doubles the exercise corpus and adds a curriculum tree that is mostly but not entirely overlapping. It is also being wound down and will be irrelevant to new students by 2029. My inclination is out for M0 and M1, revisit later if you need exercise volume, but that depends on whether your content targets current school leavers or adult retakers.
3. **What is M0's actual success metric?** "Which extractor is best" is not decidable. "Which extractor recovers ≥95% of exercise boundaries validated against the marking scheme, at acceptable cost per page" is. I would define the metric before running anything, and I would weight boundary recovery above formula fidelity, consistent with what you said matters.
4. **Verbatim exercise text: stored, or only referenced?** This is a schema decision with legal consequences and it is much cheaper to make now. Storing an exercise ID, its metadata, its concept links and a pointer into the source PDF is legally clean and probably sufficient for episode planning. Storing full task text is more useful and more exposed. If you want both, add the `verbatim_ok` flag in M1 rather than retrofitting.
5. **Parallel versions A and B: separate rows, or one row with variants?** Affects your uniqueness constraints and your dedup strategy.
6. **Where does the curriculum tree's ground truth come from?** Dz.U. 2024 poz. 1019 is a large regulation covering every subject. Extracting just the maths annex, at both levels, in a way that preserves the numbering (I. Liczby rzeczywiste, II. Wyrażenia algebraiczne, and so on) is itself an extraction task, and arguably it belongs in M0 rather than M1 since it is the same class of problem.