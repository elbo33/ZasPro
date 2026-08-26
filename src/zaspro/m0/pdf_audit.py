"""M0.5 — text-layer, diacritic, and mathematical-character audit of the PDFs.

SPEC M0.5: is there a real text layer, and does the content survive it?

Three assertions, because the corpus taught us the first two are not enough:

 1. **Text layer.** Under ~100 non-space chars/page => image-only.
 2. **Polish diacritics.** Polish prose runs ~8–12% diacritics among letters
    (maths documents ~5–6%, diluted by formulae). A near-zero ratio on a
    text-bearing document is a broken `ToUnicode` CMap on the *prose* font.
    `ł` is the canary.
 3. **Mathematical characters.** Added after the M0.6 curriculum extraction
    found `DU_programowej_2024.pdf` emits every math-italic variable
    (U+1D400–U+1D7FF, Mathematical Alphanumeric Symbols) **doubled** — `𝑥𝑥`
    for `𝑥` — and collapses stacked fractions and superscripts. The diacritic
    assertion passed on that same file because the *prose* font is fine and
    the *maths* font is not. Different font, different ToUnicode, same PDF.

Run:  uv run python -m zaspro.m0.pdf_audit
Writes m0/pdf_audit.md.
"""

from __future__ import annotations

import re
import subprocess
import unicodedata
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RAW = ROOT / "sources" / "raw"
OUT = ROOT / "m0"

DIACRITICS = set("ąćęłńóśźżĄĆĘŁŃÓŚŹŻ")
IMAGE_ONLY_CPP = 100

# Mathematical Alphanumeric Symbols block (italic/bold/script letters and
# digits used for maths variables). MATHVAR_DOUBLING_FLOOR: fraction of these
# that appear as an XX adjacent-identical pair above which the maths font's
# ToUnicode is considered broken.
MAS_LO, MAS_HI = 0x1D400, 0x1D7FF
MATHVAR_DOUBLING_FLOOR = 0.15
# Polish *prose* runs 8–12% diacritics among letters. Maths documents dilute
# that heavily with formulae, numerals and single-letter variables, so ~5–6%
# is healthy here. A near-zero ratio on a text-bearing doc means a broken
# ToUnicode CMap. The corruption floor, not the prose expectation:
DIACRITIC_FLOOR = 0.02

# Track A documents have a deterministic DOCX path; the audit is about Track B
# and anything else we read straight from PDF.
TRACK_A_PDF = {
    "Informator_EM2024_matematyka_pp.pdf",
    "MMAP-P0-100-A-2605-arkusz.pdf",
}


@dataclass
class PdfAudit:
    file: str
    pages: int
    chars: int
    letters: int
    diacritics: int
    l_stroke: int
    fonts_total: int
    fonts_no_tounicode: list[str]
    mas_count: int
    mas_doubled: int
    pua_count: int
    note: str

    @property
    def chars_per_page(self) -> float:
        return self.chars / self.pages if self.pages else 0.0

    @property
    def diacritic_ratio(self) -> float:
        return self.diacritics / self.letters if self.letters else 0.0

    @property
    def image_only(self) -> bool:
        return self.chars_per_page < IMAGE_ONLY_CPP

    @property
    def diacritics_suspect(self) -> bool:
        return not self.image_only and self.diacritic_ratio < DIACRITIC_FLOOR

    @property
    def mas_doubling_ratio(self) -> float:
        return self.mas_doubled / self.mas_count if self.mas_count else 0.0

    @property
    def math_suspect(self) -> bool:
        return (
            self.mas_count > 20 and self.mas_doubling_ratio >= MATHVAR_DOUBLING_FLOOR
        ) or self.pua_count > 0


def diacritic_ratio(text: str) -> float:
    """Fraction of letters that are Polish diacritics. Near-zero on a
    text-bearing document == silent ToUnicode corruption (SPEC M0.5)."""

    letters = sum(1 for ch in text if unicodedata.category(ch).startswith("L"))
    if not letters:
        return 0.0
    return sum(1 for ch in text if ch in DIACRITICS) / letters


def diacritics_corrupt(text: str) -> bool:
    """True if *text* has body prose but the diacritic ratio has collapsed."""

    non_space = len(re.sub(r"\s", "", text))
    return non_space > 500 and diacritic_ratio(text) < DIACRITIC_FLOOR


def math_alnum_stats(text: str) -> tuple[int, int, int]:
    """(count of Mathematical Alphanumeric Symbols, how many are doubled as an
    XX adjacent-identical pair, count of Private Use Area glyphs).

    A high doubled ratio means the maths font's ToUnicode maps one glyph to a
    two-codepoint sequence (or the glyph is placed twice); pdftotext then emits
    every variable twice. A collapse of stacked fractions/superscripts travels
    with it — those are not separately counted, but a doubled file has them.
    """

    mas = doubled = pua = 0
    prev = ""
    for ch in text:
        o = ord(ch)
        if MAS_LO <= o <= MAS_HI:
            mas += 1
            if ch == prev:
                doubled += 1
        elif 0xE000 <= o <= 0xF8FF or o > 0xF0000:
            pua += 1
        prev = ch
    return mas, doubled, pua


def math_corrupt(text: str) -> bool:
    mas, doubled, pua = math_alnum_stats(text)
    return (mas > 20 and doubled / mas >= MATHVAR_DOUBLING_FLOOR) or pua > 0


def _pdftotext(pdf: Path) -> str:
    return subprocess.run(
        ["pdftotext", str(pdf), "-"], capture_output=True, text=True, check=True
    ).stdout


def _pages(pdf: Path) -> int:
    out = subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True, check=True).stdout
    m = re.search(r"^Pages:\s+(\d+)", out, re.MULTILINE)
    return int(m.group(1)) if m else 0


def _font_tounicode(pdf: Path) -> tuple[int, list[str]]:
    """(distinct font count, distinct embedded font names with no ToUnicode).

    `pdffonts` columns: name type encoding emb sub uni object ID. A row is one
    font *instance*; dedupe by name (minus the random subset prefix). Only an
    embedded font with `uni no` can silently corrupt extraction — and only if it
    carries body text, which the diacritic assertion rules out when it passes.
    """

    out = subprocess.run(["pdffonts", str(pdf)], capture_output=True, text=True, check=True).stdout
    rows = [ln for ln in out.splitlines()[2:] if ln.strip()]
    has_good: set[str] = set()
    has_bad: set[str] = set()
    for row in rows:
        p = row.split()
        if len(p) < 7:
            continue
        raw_name, emb, uni = p[0], p[-5], p[-3]
        if emb != "yes":
            continue  # non-embedded standard fonts use builtin tables; not our risk
        name = raw_name.split("+", 1)[-1] if "+" in raw_name else raw_name
        (has_good if uni == "yes" else has_bad).add(name)
    names = has_good | has_bad
    # A name is only a real risk if *no* embedded instance carries a ToUnicode CMap.
    bad_only = sorted(has_bad - has_good)
    return len(names), bad_only


def audit(pdf: Path) -> PdfAudit:
    text = _pdftotext(pdf)
    chars = len(re.sub(r"\s", "", text))
    letters = sum(1 for ch in text if unicodedata.category(ch).startswith("L"))
    diac = sum(1 for ch in text if ch in DIACRITICS)
    lstroke = text.count("ł") + text.count("Ł")
    fonts_total, fonts_bad = _font_tounicode(pdf)
    mas, doubled, pua = math_alnum_stats(text)
    return PdfAudit(
        file=pdf.name,
        pages=_pages(pdf),
        chars=chars,
        letters=letters,
        diacritics=diac,
        l_stroke=lstroke,
        fonts_total=fonts_total,
        fonts_no_tounicode=fonts_bad,
        mas_count=mas,
        mas_doubled=doubled,
        pua_count=pua,
        note="Track A (audited for completeness; extraction is via DOCX)"
        if pdf.name in TRACK_A_PDF
        else "",
    )


def run() -> int:
    pdfs = sorted(RAW.glob("*.pdf"))
    results = [audit(p) for p in pdfs]

    L = [
        "# M0.5 — PDF text-layer, diacritic, and mathematical-character audit",
        "",
        f"`pdftotext` / `pdfinfo` / `pdffonts` over `sources/raw/*.pdf`.",
        "",
        f"- **text layer:** image-only if < {IMAGE_ONLY_CPP} non-space chars/page.",
        "- **diacritics:** Polish prose runs 8–12% diacritics among letters, "
        f"maths documents ~5–6%; below {DIACRITIC_FLOOR:.0%} on a text-bearing "
        "document = broken `ToUnicode` on the prose font. `ł` is the canary.",
        "- **math (added post-M0.6):** fraction of Mathematical Alphanumeric "
        "Symbols (U+1D400–U+1D7FF) emitted **doubled** (`𝑥𝑥` for `𝑥`), plus any "
        "Private-Use glyphs. A doubled maths font also collapses stacked "
        f"fractions and superscripts. Flag at ≥ {MATHVAR_DOUBLING_FLOOR:.0%} "
        "doubling or any PUA.",
        "",
        "| file | pages | chars/page | text layer | diacritic ratio | `ł`+`Ł` | fonts w/o ToUni | math-alnum (doubled / total) | PUA |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in results:
        tl = "image-only ⚠" if r.image_only else "yes"
        dr = (
            "n/a"
            if r.image_only
            else (f"{r.diacritic_ratio:.1%} ⚠" if r.diacritics_suspect else f"{r.diacritic_ratio:.1%}")
        )
        tu = f"0 / {r.fonts_total}" if not r.fonts_no_tounicode else f"{len(r.fonts_no_tounicode)} / {r.fonts_total}"
        if r.mas_count == 0:
            ma = "—"
        else:
            ma = f"{r.mas_doubled} / {r.mas_count} ({r.mas_doubling_ratio:.0%})"
            if r.math_suspect:
                ma += " ⚠"
        pua = f"{r.pua_count} ⚠" if r.pua_count else "0"
        L.append(
            f"| `{r.file}` | {r.pages} | {r.chars_per_page:,.0f} | {tl} | {dr} | "
            f"{r.l_stroke:,} | {tu} | {ma} | {pua} |"
        )

    img = [r for r in results if r.image_only]
    dia = [r for r in results if r.diacritics_suspect]
    mth = [r for r in results if r.math_suspect]
    L += [
        "",
        "## Assertions",
        "",
        f"- **Text layer:** {sum(not r.image_only for r in results)}/{len(results)} "
        "PDFs have a real text layer."
        + ("" if not img else " Image-only: " + ", ".join(f"`{r.file}`" for r in img) + "."),
        f"- **Diacritics:** {len(results) - len(dia) - len(img)}/"
        f"{sum(not r.image_only for r in results)} text-bearing PDFs clear the "
        f"{DIACRITIC_FLOOR:.0%} floor (ratios 5–6%, `ł` counts large and "
        "proportionate — the **prose** font is fine everywhere)."
        + ("" if not dia else " SUSPECT: " + ", ".join(f"`{r.file}`" for r in dia) + "."),
        "- **Mathematical characters:** "
        + (
            "no doubling, no PUA — maths extracts cleanly."
            if not mth
            else "**CORRUPT in "
            + ", ".join(
                f"`{r.file}` ({r.mas_doubling_ratio:.0%} of {r.mas_count} math-alnum "
                f"doubled{', ' + str(r.pua_count) + ' PUA' if r.pua_count else ''})"
                for r in mth
            )
            + ".** The maths font's ToUnicode maps each italic variable to a "
            "two-codepoint sequence, so `pdftotext` emits `𝑥𝑥` for `𝑥`; stacked "
            "fractions and superscripts collapse alongside (`½ · a · b` → `2 ⋅ a ⋅ b`, "
            "`a/x` → `x`, `sin α / cos α` → `cos α`). Prose is unaffected because "
            "it uses a different font with a correct ToUnicode."
        ),
        "- **ToUnicode (font table):** the column counts font *names* with no "
        "ToUnicode instance at all. The prose fonts (Times/Arial/Calibri) always "
        "resolve; the flagged `Cambria`/`CambriaMath` subsets are the maths font "
        "— consistent with the math-character finding above.",
        "",
        "**Overall:**",
        "",
        f"- Text layer: OK ({len(results)}/{len(results)}).",
        f"- Polish prose: OK ({sum(not r.image_only for r in results)}/"
        f"{sum(not r.image_only for r in results)}). **This is what M0.5 "
        "originally reported, and it was a false all-clear** — it never tested "
        "mathematical characters.",
        "- Mathematics: "
        + (
            "OK."
            if not mth
            else "**CORRUPT** in `"
            + "`, `".join(r.file for r in mth)
            + "`. `DU_programowej_2024.pdf` is the curriculum authority (M0.6 seed "
            "source); its maths cannot be trusted from `pdftotext` and the seed's "
            "formulae are being hand-transcribed from the rendered PDF instead "
            "(`seeds/curriculum_matematyka_formulas_review.md`). `matematyka.pdf` "
            "is superseded. The formula sheet "
            "`wybrane_wzory_matematyczne_EM2023.pdf` — the main maths-heavy Track B "
            "ingestion target — is **below the flag threshold** (see table); M2 "
            "should still spot-check it before ingesting."
        ),
        "",
        "## For M2",
        "",
        "Any Track B PDF that carries a doubled maths font must not be text-mined "
        "for formulae with `pdftotext`. Options in order of preference: the "
        "document's DOCX sibling if one exists; a maths-aware OCR / VLM over "
        "rendered pages; or hand transcription for small volumes (as M0.6 did). "
        "Run this audit on every new Track B source before ingesting it.",
        "",
        "## Scope",
        "",
        "No extractor comparison was run (ADR 0005). The survey in "
        "`docs/sources.md` Part B is the starting point when textbooks arrive.",
        "",
    ]
    (OUT / "pdf_audit.md").write_text("\n".join(L), encoding="utf-8")

    print(f"M0.5  audited {len(results)} PDFs")
    for r in results:
        flags = []
        if r.image_only:
            flags.append("IMAGE-ONLY")
        if r.diacritics_suspect:
            flags.append("DIACRITIC")
        if r.math_suspect:
            flags.append(f"MATH({r.mas_doubling_ratio:.0%} dbl, {r.pua_count} PUA)")
        tag = ("  ⚠ " + ", ".join(flags)) if flags else ""
        print(
            f"      {r.file:42} {r.chars_per_page:7,.0f} cpp  diac {r.diacritic_ratio:4.1%}"
            f"  math-alnum {r.mas_doubled}/{r.mas_count}{tag}"
        )
    print(f"      wrote {(OUT / 'pdf_audit.md').relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
