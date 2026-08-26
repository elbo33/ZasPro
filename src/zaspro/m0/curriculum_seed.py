"""M0.6 — one-off extraction of the mathematics curriculum tree.

NOT a pipeline (SPEC M0.6). This is a single-use scaffold that parses the
mathematics annex of Dz.U. 2024 poz. 1019 into a draft tree. The output is
then hand-verified node by node against the regulation text and committed as
`seeds/curriculum_matematyka.yaml`; this script is not run again.

Source: `sources/raw/DU_programowej_2024.pdf`, "Treści nauczania – wymagania
szczegółowe" for liceum ogólnokształcące / technikum.

`matematyka.pdf` (the CKE `_OD_2015` extract) was checked first and DISCARDED —
its requirement text diverges from the 2024 amendment (see
`m0/curriculum_notes.md`). Per SPEC M0.6, the Dz.U. text wins.

Run:  uv run python -m zaspro.m0.curriculum_seed
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DU_PDF = ROOT / "sources" / "raw" / "DU_programowej_2024.pdf"
OUT_YAML = ROOT / "seeds" / "curriculum_matematyka.yaml"

# ---------------------------------------------------------------------------
# Hand-transcribed formulae.
#
# `pdftotext` corrupts the maths in DU_programowej_2024.pdf (M0.5): every
# math-italic variable is doubled and stacked fractions/superscripts collapse,
# turning `½·a·b` into `2·a·b`, `a/x` into `x`, `sin α / cos α` into `cos α`.
# So the requirement prose and its formula are separated here:
#   name             -- prose only, plain text, variables as ordinary letters
#   statement_latex  -- the formula, valid LaTeX, transcribed from the RENDERED
#                       PDF (pages 327-335), not from the extracted text
#   rendered         -- verbal description of the PDF appearance, for review
#   extracted        -- what pdftotext produced, to show the delta
#   corrupt          -- True if extraction changed the maths (not just noise)
#
# Verified by a human in seeds/curriculum_matematyka_formulas_review.md.
# ---------------------------------------------------------------------------
FORMULA_ROWS: dict[str, dict[str, object]] = {
    "I.5": {
        "name": "stosuje monotoniczność potęgowania, w szczególności własności dla podstawy większej niż 1 oraz z przedziału (0, 1)",
        "statement_latex": r"x<y \,\land\, a>1 \;\Rightarrow\; a^{x}<a^{y}; \qquad x<y \,\land\, 0<a<1 \;\Rightarrow\; a^{x}>a^{y}",
        "rendered": "inline: „jeśli x < y oraz a > 1, to aˣ < aʸ, zaś gdy x < y i 0 < a < 1, to aˣ > aʸ” — x, y, a italic; the a-terms have raised superscript exponents x and y",
        "extracted": "… to ax < ay, zaś gdy x < y i 0 < a < 1, to ax > ay",
        "corrupt": True,
    },
    "I.7": {
        "name": "stosuje interpretację geometryczną i algebraiczną wartości bezwzględnej, rozwiązuje proste równania z wartością bezwzględną",
        "statement_latex": r"|x + 4| = 5",
        "rendered": "„rozwiązuje równania typu: |x + 4| = 5”",
        "extracted": "rozwiązuje równania typu: |x + 4| = 5",
        "corrupt": False,
    },
    "II.1": {
        "name": "stosuje wzory skróconego mnożenia na kwadrat sumy, kwadrat różnicy i różnicę kwadratów",
        "statement_latex": r"(a+b)^{2}, \quad (a-b)^{2}, \quad a^{2}-b^{2}",
        "rendered": "„(a + b)², (a − b)², a² − b²” — superscript 2",
        "extracted": "(a + b)2, (a − b)2, a2 − b2",
        "corrupt": True,
    },
    "II.R1": {
        "name": "dzieli wielomian jednej zmiennej przez dwumian postaci x minus a",
        "statement_latex": r"W(x) : (x - a)",
        "rendered": "„dzieli wielomian jednej zmiennej W(x) przez dwumian postaci x − a”",
        "extracted": "dzieli wielomian jednej zmiennej W(x) przez dwumian postaci x − a",
        "corrupt": False,
    },
    "II.R4": {
        "name": "stosuje podstawowe własności trójkąta Pascala oraz następujące własności współczynnika dwumianowego (symbolu Newtona)",
        "statement_latex": r"\binom{n}{0}=1, \quad \binom{n}{1}=n, \quad \binom{n}{n-1}=n, \quad \binom{n}{k}=\binom{n}{n-k}, \quad \binom{n}{k}+\binom{n}{k+1}=\binom{n+1}{k+1}",
        "rendered": "five identities, each with binomial coefficients written vertically as (n over k) inside round brackets",
        "extracted": "(𝑛𝑛0) = 1, (𝑛𝑛1) = 𝑛𝑛, 𝑛𝑛 (𝑛𝑛−1 ) = 𝑛𝑛, (𝑛𝑛𝑘𝑘) = (𝑛𝑛−𝑘𝑘 𝑛𝑛 ), (𝑛𝑛𝑘𝑘) + (𝑘𝑘+1 𝑛𝑛 ) = (𝑛𝑛+1 𝑘𝑘+1 )",
        "corrupt": True,
    },
    "II.R5": {
        "name": "korzysta ze wzorów na sumę i różnicę sześcianów, różnicę n-tych potęg oraz n-tą potęgę sumy i różnicy",
        "statement_latex": r"a^{3}+b^{3}, \quad a^{3}-b^{3}, \quad a^{n}-b^{n}, \quad (a+b)^{n}, \quad (a-b)^{n}",
        "rendered": "„a³ + b³, a³ − b³, aⁿ − bⁿ, (a + b)ⁿ i (a − b)ⁿ” — superscript 3 and n",
        "extracted": "a3 + b3, a3 − b3, an − bn, (a + b)n i (a − b)n  [+ fragments of R6 bled in]",
        "corrupt": True,
    },
    "II.R6": {
        "name": "dodaje i odejmuje wyrażenia wymierne w przypadkach nie trudniejszych niż podane przykłady",
        "statement_latex": r"\frac{1}{x+1}-\frac{1}{x}; \qquad \frac{1}{x}+\frac{1}{x^{2}}+\frac{1}{x^{3}}; \qquad \frac{x+1}{x+2}+\frac{x-1}{x+1}",
        "rendered": "three example expressions, each a sum/difference of proper fractions (numerator stacked over denominator)",
        "extracted": "𝑥𝑥 +1 − 𝑥𝑥, 𝑥𝑥 + 𝑥𝑥 2 + 𝑥𝑥 3, 𝑥𝑥 + 2 + 𝑥𝑥 + 1",
        "corrupt": True,
    },
    "III.1": {
        "name": "przekształca równania i nierówności w sposób równoważny, w tym równania wymierne prowadzące do równania liniowego",
        "statement_latex": r"\frac{5}{x+1}=\frac{x+3}{2x-1}",
        "rendered": "„przekształca równoważnie równanie 5/(x+1) = (x+3)/(2x−1)” — two proper fractions either side of the equals sign",
        "extracted": "przekształca 5 𝑥𝑥 + 3 równoważnie równanie 𝑥𝑥 + 1 = 2𝑥𝑥−1",
        "corrupt": True,
    },
    "III.5": {
        "name": "rozwiązuje równania wielomianowe dla wielomianów doprowadzonych do postaci iloczynowej",
        "statement_latex": r"W(x) = 0",
        "rendered": "„równania wielomianowe postaci W(x) = 0”",
        "extracted": "równania wielomianowe postaci W(x) = 0",
        "corrupt": False,
    },
    "III.R1": {
        "name": "rozwiązuje równania i nierówności wielomianowe dla wielomianów doprowadzonych do postaci iloczynowej (także przez wyłączanie czynnika lub grupowanie)",
        "statement_latex": r"W(x)=0; \qquad W(x)>0,\; W(x)\ge 0,\; W(x)<0,\; W(x)\le 0",
        "rendered": "„W(x) = 0 oraz nierówności wielomianowe typu: W(x) > 0, W(x) ≥ 0, W(x) < 0, W(x) ≤ 0”",
        "extracted": "W(x) = 0 oraz nierówności wielomianowe typu: W(x) > 0, W(x) ≥ 0, W(x) < 0, W(x) ≤ 0",
        "corrupt": False,
    },
    "III.R7": {
        "name": "rozwiązuje równania wymierne, których licznik i mianownik są zapisane w postaci iloczynowej",
        "statement_latex": r"\frac{V(x)}{W(x)} = 0",
        "rendered": "„równania wymierne postaci V(x)/W(x) = 0, gdzie wielomiany V(x) i W(x) są zapisane w postaci iloczynowej”",
        "extracted": "postaci 𝑉𝑉(𝑥𝑥)/𝑊𝑊(𝑥𝑥)= 0ǡ gdzie wielomiany 𝑉𝑉(𝑥𝑥) i 𝑊𝑊(𝑥𝑥)   [comma → U+01E1 ‘ǡ’]",
        "corrupt": True,
    },
    "IV.R1": {
        "name": "rozwiązuje układy równań liniowych i kwadratowych z dwiema niewiadomymi, które można sprowadzić do równania kwadratowego lub liniowego i które nie są trudniejsze niż podany przykład",
        "statement_latex": r"\begin{cases} x^{2}+y^{2}+ax+by=c \\ x^{2}+y^{2}+dx+ey=f \end{cases}",
        "rendered": "a two-equation system in a large brace, each equation of the form x² + y² + (linear terms) = const",
        "extracted": "𝑥𝑥 2 + 𝑦𝑦 2 + 𝑎𝑎𝑎𝑎 + 𝑏𝑏𝑏𝑏 = 𝑐𝑐  {  .  𝑥𝑥 2 + 𝑦𝑦 2 + 𝑑𝑑𝑑𝑑 + 𝑒𝑒𝑒𝑒 = 𝑓𝑓",
        "corrupt": True,
    },
    "V.12": {
        "name": "na podstawie wykresu funkcji y = f(x) szkicuje wykresy funkcji powstałych przez przesunięcie wzdłuż osi",
        "statement_latex": r"y=f(x) \;\longrightarrow\; y=f(x-a), \quad y=f(x)+b",
        "rendered": "„y = f(x) szkicuje wykresy funkcji y = f(x − a), y = f(x) + b”",
        "extracted": "𝑦𝑦 = 𝑓𝑓(𝑥𝑥) szkicuje wykresy funkcji 𝑦𝑦 = 𝑓𝑓(𝑥𝑥 − 𝑎𝑎), 𝑦𝑦 = 𝑓𝑓(𝑥𝑥) + 𝑏𝑏",
        "corrupt": True,
    },
    "V.13": {
        "name": "posługuje się funkcją odwrotnie proporcjonalną, w tym jej wykresem, do opisu i interpretacji zagadnień związanych z wielkościami odwrotnie proporcjonalnymi",
        "statement_latex": r"f(x)=\frac{a}{x}",
        "rendered": "„posługuje się funkcją f(x) = a/x” — a stacked over x as a fraction",
        "extracted": "posługuje się funkcją 𝑓𝑓(𝑥𝑥) = 𝑥𝑥   [the ‘a’ and the fraction bar are GONE]",
        "corrupt": True,
    },
    "V.R1": {
        "name": "na podstawie wykresu funkcji y = f(x) rysuje wykresy funkcji powstałych przez odbicie względem osi",
        "statement_latex": r"y=f(x) \;\longrightarrow\; y=-f(x), \quad y=f(-x)",
        "rendered": "„y = f(x) rysuje wykresy funkcji y = −f(x), y = f(−x)”",
        "extracted": "𝑦𝑦 = 𝑓𝑓(𝑥𝑥) rysuje wykresy funkcji 𝑦𝑦 = −𝑓𝑓(𝑥𝑥), 𝑦𝑦 = 𝑓𝑓(−𝑥𝑥)",
        "corrupt": True,
    },
    "V.R3": {
        "name": "dowodzi monotoniczności funkcji zadanej wzorem, jak w przykładzie: wykazanie, że dana funkcja wymierna jest monotoniczna w podanym przedziale",
        "statement_latex": r"f(x)=\frac{x-1}{x+2} \quad \text{monotoniczna w} \quad (-\infty,\,-2)",
        "rendered": "„wykaż, że funkcja f(x) = (x−1)/(x+2) jest monotoniczna w przedziale (−∞, −2)” — (x−1) stacked over (x+2)",
        "extracted": "wykaż, że funkcja 𝑥𝑥−1 𝑓𝑓(𝑥𝑥) = 𝑥𝑥+2 jest monotoniczna w przedziale (−∞, −2)",
        "corrupt": True,
    },
    "VI.R1": {
        "name": "oblicza granice ciągów, korzystając z granic ciągów wzorcowych (typu 1/n oraz n-tego pierwiastka z a) oraz twierdzeń o granicy sumy, różnicy, iloczynu i ilorazu ciągów zbieżnych, a także twierdzenia o trzech ciągach",
        "statement_latex": r"\tfrac{1}{n}, \quad \sqrt[n]{a}",
        "rendered": "„granic ciągów typu 1/n, ⁿ√a” — 1 stacked over n; and an n-th root of a (small n above the radical)",
        "extracted": "granic ciągów typu 𝑛𝑛, 𝑛𝑛√𝑎𝑎   [the ‘1’ numerator is GONE; ⁿ√a lost its index]",
        "corrupt": True,
    },
    "VII.2": {
        "name": "korzysta z jedynki trygonometrycznej oraz z definicji tangensa jako ilorazu sinusa i cosinusa",
        "statement_latex": r"\sin^{2}\alpha+\cos^{2}\alpha=1; \qquad \operatorname{tg}\alpha=\frac{\sin\alpha}{\cos\alpha}",
        "rendered": "„sin²α + cos²α = 1, tg α = sin α / cos α” — the tangent identity has sin α stacked over cos α",
        "extracted": "sin2 𝛼𝛼 + cos 2 𝛼𝛼 = 1, tg 𝛼𝛼 = cos 𝛼𝛼   [the ‘sin α’ numerator is GONE]",
        "corrupt": True,
    },
    "VII.3": {
        "name": "stosuje twierdzenie cosinusów oraz wzór na pole trójkąta wyrażone przez dwa boki i sinus kąta między nimi",
        "statement_latex": r"P=\tfrac{1}{2}\,a\,b\,\sin\gamma",
        "rendered": "„wzór na pole trójkąta P = ½ · a · b · sin γ” — one-half as a fraction",
        "extracted": "wzór na pole trójkąta 𝑃𝑃 = 2 ⋅ 𝑎𝑎 ⋅ 𝑏𝑏 ⋅ sin 𝛾𝛾   [½ became 2 — the formula is now wrong]",
        "corrupt": True,
    },
    "IX.4": {
        "name": "posługuje się równaniem okręgu w postaci kanonicznej",
        "statement_latex": r"(x-a)^{2}+(y-b)^{2}=r^{2}",
        "rendered": "„(x − a)² + (y − b)² = r²” — superscript 2 throughout",
        "extracted": "(𝑥𝑥 − 𝑎𝑎)2 + (𝑦𝑦 − 𝑏𝑏)2 = 𝑟𝑟 2",
        "corrupt": True,
    },
}

# 1-indexed pdftotext -layout line span of the annex (I. Liczby rzeczywiste ..
# just before "Warunki i sposób realizacji"). Verified by hand.
ANNEX_FIRST_LINE = 13750
ANNEX_LAST_LINE = 14123

_SECTION = re.compile(r"^\s{2,}([IVX]{1,4})\.\s+(.+?)\.?\s*$")
_ZP = re.compile(r"^\s*Zakres podstawowy\.\s*Uczeń(:|.*?)\s*$")
_ZR = re.compile(r"^\s*Zakres rozszerzony\.\s*Uczeń spełnia wymagania(.*?)\s*$")
_NUM = re.compile(r"^\s*(\d+)\)\s+(.*)$")
_SUB = re.compile(r"^\s*([a-z])\)\s+(.*)$")
_NOISE = re.compile(r"(Dziennik Ustaw|Poz\.\s*1019|^\s*[–-]+\s*\d+|^\s*\d+\s*[–-]\s*$|^\s*﻿)")


def _annex_lines() -> list[str]:
    raw = subprocess.run(
        ["pdftotext", "-layout", str(DU_PDF), "-"], capture_output=True, text=True, check=True
    ).stdout.splitlines()
    seg = raw[ANNEX_FIRST_LINE - 1 : ANNEX_LAST_LINE]
    return [ln.rstrip() for ln in seg if not _NOISE.search(ln)]


def _clean(text: str) -> str:
    t = re.sub(r"\s+", " ", text).strip()
    # pdftotext -layout floats stacked-fraction fragments from the NEXT numbered
    # item up between lines; they land after this item's terminal ';'. Drop a
    # trailing segment that carries no real word.
    head, sep, tail = t.rpartition(";")
    if sep and tail and not re.search(r"[A-Za-zĄĆĘŁŃÓŚŹŻąćęłńóśźż]{4,}", tail):
        t = head
    return t.strip().rstrip(";.").strip()


def parse() -> list[dict]:
    units: list[dict] = []
    unit: dict | None = None
    level: str | None = None
    items: list[dict] = []  # current level's items
    cur: dict | None = None  # current numbered item (for continuation lines)
    inline_zr_pending = False

    def flush_item() -> None:
        nonlocal cur
        if cur is not None:
            cur["raw"] = re.sub(r"\s+", " ", cur["statement"]).strip()
            cur["statement"] = _clean(cur["statement"])
            for sp in cur.get("subpoints", []):
                sp["raw"] = re.sub(r"\s+", " ", sp["statement"]).strip()
                sp["statement"] = _clean(sp["statement"])
            items.append(cur)
            cur = None

    for ln in _annex_lines():
        s = _SECTION.match(ln)
        if s and s.group(1) in {
            "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII", "XIII",
        }:
            flush_item()
            unit = {
                "code": s.group(1),
                "name": _clean(s.group(2)),
                "raw": re.sub(r"\s+", " ", ln).strip(),
                "topics": [],
            }
            units.append(unit)
            level = None
            items = unit["topics"]
            continue

        if unit is None:
            continue

        if _ZP.match(ln):
            flush_item()
            level = "podstawowy"
            # "Zakres podstawowy. Uczeń <inline single requirement>." — keep cur
            # open so continuation lines are appended; it flushes at the next marker.
            tail = ln.split("Uczeń", 1)[1].strip().lstrip(":").strip()
            if tail and not tail.endswith(":"):
                cur = {"code": f"{unit['code']}.1", "level": level, "statement": tail}
            continue

        z = _ZR.match(ln)
        if z:
            flush_item()
            level = "rozszerzony"
            tail = z.group(1).strip()
            # "...a ponadto <single requirement>."  vs  "...a ponadto:"
            if tail.endswith(":"):
                inline_zr_pending = False
            elif "a ponadto" in tail:
                body = tail.split("a ponadto", 1)[1].strip()
                if body:
                    # inline single ZR requirement — keep cur open for continuation
                    cur = {"code": f"{unit['code']}.R1", "level": level, "statement": body}
                    inline_zr_pending = False
                else:
                    inline_zr_pending = True
            else:
                inline_zr_pending = True
            continue

        if inline_zr_pending and ln.strip():
            body = ln.strip()
            if body.startswith("ponadto"):
                body = body[len("ponadto"):].strip()
            if not body or body == ":":
                # "... a\nponadto:"  — a numbered list follows, no inline item
                inline_zr_pending = False
                continue
            cur = {"code": f"{unit['code']}.R1", "level": "rozszerzony", "statement": body}
            inline_zr_pending = False
            continue

        n = _NUM.match(ln)
        if n and level:
            flush_item()
            idx = n.group(1)
            code = f"{unit['code']}.{idx}" if level == "podstawowy" else f"{unit['code']}.R{idx}"
            cur = {"code": code, "level": level, "statement": n.group(2)}
            continue

        sub = _SUB.match(ln)
        if sub and cur is not None:
            cur.setdefault("subpoints", []).append(
                {"code": f"{cur['code']}{sub.group(1)}", "statement": sub.group(2)}
            )
            continue

        if cur is not None and ln.strip():
            if cur.get("subpoints"):
                cur["subpoints"][-1]["statement"] += " " + ln.strip()
            else:
                cur["statement"] += " " + ln.strip()

    flush_item()
    _apply_formula_transcriptions(units)
    return units


def _apply_formula_transcriptions(units: list[dict]) -> None:
    """Replace the pdftotext-mangled statement of a formula row with a
    prose `name` and a hand-transcribed `statement_latex` (FORMULA_ROWS)."""

    seen: set[str] = set()
    for u in units:
        for t in u["topics"]:
            fx = FORMULA_ROWS.get(t["code"])
            if fx is None:
                continue
            seen.add(t["code"])
            t["extracted_raw"] = t["statement"]  # keep for the review sheet
            t["statement"] = fx["name"]
            t["raw"] = fx["name"]
            t["statement_latex"] = fx["statement_latex"]
    missing = set(FORMULA_ROWS) - seen
    if missing:
        raise ValueError(f"FORMULA_ROWS codes not found in tree: {sorted(missing)}")


def _yaml(units: list[dict]) -> str:
    L = [
        "# ZasPro curriculum seed — Mathematics (Formuła 2023).",
        "#",
        "# Source of truth: Dz.U. 2024 poz. 1019 (Rozporządzenie MEN z 28.06.2024),",
        "#   matematyka annex for liceum ogólnokształcące / technikum,",
        "#   \"Treści nauczania – wymagania szczegółowe\".",
        "# Extracted from sources/raw/DU_programowej_2024.pdf on 2026-08-26 (M0.6).",
        "#",
        "# matematyka.pdf (CKE _OD_2015 extract) was checked and DISCARDED: its",
        "#   requirement text diverges from the 2024 amendment. See",
        "#   m0/curriculum_notes.md for the spot-check.",
        "#",
        "# rozszerzony = podstawowy + additions (\"a ponadto\"). Additions carry an",
        "#   R in the code (I.R1) to stay unique alongside the podstawowy codes.",
        "#",
        "# STATUS: DRAFT — every node must be verified by a human before M1",
        "#   seeds from this file. Two review sheets:",
        "#   - curriculum_matematyka_review.md          all 132 nodes, Dz.U. order",
        "#   - curriculum_matematyka_formulas_review.md  the formula rows only",
        "#",
        "# `pdftotext` corrupts the maths in DU_programowej_2024.pdf (M0.5): every",
        "#   math-italic variable is doubled and stacked fractions/superscripts",
        "#   collapse. So a requirement's prose lives in `name` and its formula in",
        "#   `statement_latex`, hand-transcribed from the RENDERED PDF. `name`",
        "#   without `statement_latex` means the requirement carries no formula.",
        "",
        "subject:",
        "  name: Matematyka",
        "  slug: matematyka",
        "  language: pl",
        "  levels: [podstawowy, rozszerzony]",
        "  official_source: \"Dz.U. 2024 poz. 1019\"",
        "  status: DRAFT",
        "",
        "units:",
    ]
    for i, u in enumerate(units, 1):
        L.append(f"  - code: {u['code']}")
        L.append(f"    name: {_q(u['name'])}")
        L.append(f"    order_index: {i}")
        L.append("    topics:")
        for t in u["topics"]:
            L.append(f"      - code: {t['code']}")
            L.append(f"        level: {t['level']}")
            L.append(f"        name: {_q(t['statement'])}")
            if t.get("statement_latex"):
                L.append(f"        statement_latex: {_q(t['statement_latex'])}")
            for sp in t.get("subpoints", []):
                L.append(f"        # {sp['code']}: {sp['statement']}")
    L.append("")
    return "\n".join(L)


def _q(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _md_cell(s: str) -> str:
    return s.replace("|", "\\|")


def _review_md(units: list[dict]) -> str:
    """One line per node, in the order the regulation lists them, with the
    verbatim pdftotext span beside the cleaned seed value — for human
    verification of all ~132 nodes (SPEC M0.6)."""

    zp = sum(1 for u in units for t in u["topics"] if t["level"] == "podstawowy")
    zr = sum(1 for u in units for t in u["topics"] if t["level"] == "rozszerzony")
    L = [
        "# Curriculum seed — review sheet (M0.6)",
        "",
        "Every node of `seeds/curriculum_matematyka.yaml`, in Dz.U. order, for "
        "node-by-node verification against the regulation before M1 seeds from it.",
        "",
        "- **Source:** Dz.U. 2024 poz. 1019, Rozporządzenie MEN z 28.06.2024, "
        "matematyka annex for liceum ogólnokształcące / technikum, "
        '"Treści nauczania – wymagania szczegółowe".',
        "- **Extracted from:** `sources/raw/DU_programowej_2024.pdf` "
        f"(`pdftotext -layout`, annex lines {ANNEX_FIRST_LINE}–{ANNEX_LAST_LINE}).",
        f"- **Nodes:** {len(units)} units + {zp} podstawowy + {zr} rozszerzony = "
        f"{len(units) + zp + zr}. The 4 sub-points (I.2 a/b, XI.2 a/b) are extra "
        f"rows, so the sheet has {len(units) + zp + zr + 4} numbered lines.",
        "- **seed name** is the value in the YAML. **Dz.U. text** is the raw "
        "`pdftotext` span. For most rows they differ only in trailing punctuation "
        "and line-join whitespace.",
        "- Rows carrying a formula are marked **⚑** — for those the seed `name` is "
        "prose only and the maths is a hand-transcribed `statement_latex`; the "
        "extraction is corrupt (see `curriculum_matematyka_formulas_review.md`).",
        "",
        "| # | code | level | seed name | Dz.U. text (pdftotext) |",
        "|---|---|---|---|---|",
    ]
    i = 0
    for u in units:
        i += 1
        L.append(f"| {i} | **{u['code']}** | *unit* | **{_md_cell(u['name'])}** | {_md_cell(u['raw'])} |")
        for level in ("podstawowy", "rozszerzony"):
            for t in (x for x in u["topics"] if x["level"] == level):
                i += 1
                mark = " ⚑" if t.get("statement_latex") else ""
                dzu = t.get("extracted_raw", t["raw"])
                L.append(
                    f"| {i} | {t['code']}{mark} | {level} | {_md_cell(t['statement'])} "
                    f"| {_md_cell(dzu)} |"
                )
                for sp in t.get("subpoints", []):
                    i += 1
                    L.append(
                        f"| {i} | {sp['code']} | ↳ sub | {_md_cell(sp['statement'])} "
                        f"| {_md_cell(sp['raw'])} |"
                    )
    L.append("")
    return "\n".join(L)


def _formulas_review_md(units: list[dict]) -> str:
    """The formula rows only: hand-transcribed LaTeX vs the rendered PDF vs the
    corrupt extraction, so a human can verify without opening the PDF per line."""

    by_code = {t["code"]: (u, t) for u in units for t in u["topics"]}
    corrupt = [c for c, v in FORMULA_ROWS.items() if v["corrupt"]]
    clean = [c for c, v in FORMULA_ROWS.items() if not v["corrupt"]]

    L = [
        "# Curriculum seed — formula review (M0.6)",
        "",
        "`pdftotext` corrupts the maths in `DU_programowej_2024.pdf` (M0.5): every "
        "math-italic variable is doubled (`𝑥𝑥` for `𝑥`) and stacked "
        "fractions/superscripts collapse. So each requirement below has its prose "
        "in `name` and its formula hand-transcribed into `statement_latex` from "
        "the **rendered** PDF (pages 327–335 of `DU_programowej_2024.pdf`).",
        "",
        f"- **{len(corrupt)} rows** where extraction changed the maths — verify these first.",
        f"- **{len(clean)} rows** where extraction was clean but the formula is still "
        "given its own `statement_latex` for schema consistency.",
        "- Verify each `statement_latex` against the **rendered appearance** column; "
        "open the PDF only if that is not enough.",
        "",
    ]
    for bucket, codes, title in (
        ("A", corrupt, f"A. Extraction changed the maths ({len(corrupt)})"),
        ("B", clean, f"B. Extraction clean, transcribed anyway ({len(clean)})"),
    ):
        L += ["", f"## {title}", ""]
        for code in codes:
            fx = FORMULA_ROWS[code]
            u, t = by_code[code]
            L += [
                f"### {code} ({t['level']}) — {u['name']}",
                "",
                f"- **seed name:** {fx['name']}",
                f"- **statement_latex:** `{fx['statement_latex']}`",
                f"- **rendered in PDF:** {fx['rendered']}",
                f"- **pdftotext gave:** `{fx['extracted']}`",
                "",
            ]
    return "\n".join(L)


def run() -> int:
    units = parse()
    OUT_YAML.parent.mkdir(exist_ok=True)
    OUT_YAML.write_text(_yaml(units), encoding="utf-8")
    review = OUT_YAML.with_name("curriculum_matematyka_review.md")
    review.write_text(_review_md(units), encoding="utf-8")
    freview = OUT_YAML.with_name("curriculum_matematyka_formulas_review.md")
    freview.write_text(_formulas_review_md(units), encoding="utf-8")

    zp = sum(1 for u in units for t in u["topics"] if t["level"] == "podstawowy")
    zr = sum(1 for u in units for t in u["topics"] if t["level"] == "rozszerzony")
    subs = sum(len(t.get("subpoints", [])) for u in units for t in u["topics"])
    print(f"M0.6  {len(units)} units, {zp} podstawowy + {zr} rozszerzony topics, {subs} subpoints")
    for u in units:
        p = sum(1 for t in u["topics"] if t["level"] == "podstawowy")
        r = sum(1 for t in u["topics"] if t["level"] == "rozszerzony")
        print(f"      {u['code']:>4}. {u['name'][:44]:44} ZP {p:2}  ZR {r}")
    fx_corrupt = sum(1 for v in FORMULA_ROWS.values() if v["corrupt"])
    print(f"      formula rows: {len(FORMULA_ROWS)} hand-transcribed ({fx_corrupt} were corrupt)")
    print(f"      wrote {OUT_YAML.relative_to(ROOT)}  (DRAFT — verify node by node)")
    print(f"      wrote {review.relative_to(ROOT)}  ({len(units) + zp + zr} nodes)")
    print(f"      wrote {freview.relative_to(ROOT)}  ({len(FORMULA_ROWS)} formula rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
