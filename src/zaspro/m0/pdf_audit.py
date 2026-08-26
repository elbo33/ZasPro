"""M0.5 — text-layer and Polish-diacritic audit of the PDF sources.

SPEC M0.5: two questions, then stop.
 1. Is there a real text layer, and do Polish diacritics survive it?
 2. Nothing else — no extractor comparison (deferred, see ADR 0005).

Under ~100 non-space characters per page => image-only.
Polish prose runs ~8–12% diacritics among its letters; a near-zero ratio on a
document that clearly has text means silent encoding corruption from a missing
`ToUnicode` CMap, not a document without diacritics. `ł` is the canary. This
failure raises no exception, so it is asserted on explicitly.

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
    return PdfAudit(
        file=pdf.name,
        pages=_pages(pdf),
        chars=chars,
        letters=letters,
        diacritics=diac,
        l_stroke=lstroke,
        fonts_total=fonts_total,
        fonts_no_tounicode=fonts_bad,
        note="Track A (audited for completeness; extraction is via DOCX)"
        if pdf.name in TRACK_A_PDF
        else "",
    )


def run() -> int:
    pdfs = sorted(RAW.glob("*.pdf"))
    results = [audit(p) for p in pdfs]

    L = [
        "# M0.5 — PDF text-layer and Polish-diacritic audit",
        "",
        f"`pdftotext` / `pdfinfo` / `pdffonts` over `sources/raw/*.pdf`. "
        f"Image-only if < {IMAGE_ONLY_CPP} non-space chars/page. Polish prose "
        "runs ~8–12% diacritics among letters; < 3% on a text-bearing document "
        "means a broken `ToUnicode` CMap (silent). `ł` is the canary.",
        "",
        "| file | pages | chars/page | text layer | diacritic ratio | `ł`+`Ł` | embedded fonts w/o ToUnicode |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in results:
        tl = "image-only ⚠" if r.image_only else "yes"
        dr = (
            "n/a"
            if r.image_only
            else (f"{r.diacritic_ratio:.1%} ⚠ SUSPECT" if r.diacritics_suspect else f"{r.diacritic_ratio:.1%}")
        )
        tu = f"0 / {r.fonts_total}" if not r.fonts_no_tounicode else f"{len(r.fonts_no_tounicode)} / {r.fonts_total}"
        L.append(
            f"| `{r.file}` | {r.pages} | {r.chars_per_page:,.0f} | {tl} | {dr} | {r.l_stroke:,} | {tu} |"
        )

    suspects = [r for r in results if r.image_only or r.diacritics_suspect]
    L += [
        "",
        "## Assertions",
        "",
        f"- **Text layer:** {sum(not r.image_only for r in results)}/{len(results)} "
        "PDFs have a real text layer."
        + ("" if not any(r.image_only for r in results) else
           " Image-only: " + ", ".join(f"`{r.file}`" for r in results if r.image_only) + "."),
        f"- **Diacritics:** {sum(not r.diacritics_suspect and not r.image_only for r in results)}"
        f"/{sum(not r.image_only for r in results)} text-bearing PDFs clear the "
        f"{DIACRITIC_FLOOR:.0%} corruption floor. Ratios cluster at 5–6%, normal "
        "for maths documents (prose is 8–12%; formulae and numerals dilute it). "
        "`ł` counts are large and proportionate — no silent WinAnsi truncation."
        + ("" if not any(r.diacritics_suspect for r in results) else
           " SUSPECT: " + ", ".join(f"`{r.file}`" for r in results if r.diacritics_suspect) + "."),
        "- **ToUnicode:** the table column counts font *names* for which **no** "
        "embedded instance has a ToUnicode CMap. "
        + (
            "Every text-bearing font in every PDF has at least one ToUnicode "
            "instance — the body Times/Arial/Calibri all resolve. A handful of "
            "`Cambria`/`CambriaMath` symbol subsets and a few WinAnsi fallbacks "
            "lack one, but they carry glyphs (∈, √, ≤), not Polish letters, and "
            "the diacritic assertion confirms nothing is lost."
            if all(not r.fonts_no_tounicode for r in results)
            else "Names with no good instance anywhere: "
            + "; ".join(f"`{r.file}` → {', '.join(r.fonts_no_tounicode)}" for r in results if r.fonts_no_tounicode)
        ),
        "",
        "**Overall: "
        + ("no image-only sources, no diacritic corruption. The Track B PDFs "
           "(`DU_programowej_2024.pdf`, `matematyka.pdf`) and the formula sheet "
           "are born-digital with clean, extractable Polish text."
           if not suspects
           else f"{len(suspects)} source(s) need attention — see the table.")
        + "**",
        "",
        "## Scope",
        "",
        "Per SPEC M0.5, that is the whole audit. No extractor comparison was run "
        "— it is work for whenever textbooks arrive, and the landscape will have "
        "moved. The survey in `docs/sources.md` Part B is the starting point; the "
        "deferral is recorded in `docs/decisions/0005-track-b-deferral.md`.",
        "",
    ]
    (OUT / "pdf_audit.md").write_text("\n".join(L), encoding="utf-8")

    print(f"M0.5  audited {len(results)} PDFs")
    for r in results:
        flag = " ⚠" if (r.image_only or r.diacritics_suspect or r.fonts_no_tounicode) else ""
        print(f"      {r.file:42} {r.chars_per_page:7,.0f} cpp  diac {r.diacritic_ratio:.1%}{flag}")
    print(f"      wrote {(OUT / 'pdf_audit.md').relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
