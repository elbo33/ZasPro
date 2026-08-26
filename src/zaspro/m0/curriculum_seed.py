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
    return re.sub(r"\s+", " ", text).strip().rstrip(";.").strip()


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
            cur["statement"] = _clean(cur["statement"])
            for sp in cur.get("subpoints", []):
                sp["statement"] = _clean(sp["statement"])
            items.append(cur)
            cur = None

    for ln in _annex_lines():
        s = _SECTION.match(ln)
        if s and s.group(1) in {
            "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII", "XIII",
        }:
            flush_item()
            unit = {"code": s.group(1), "name": _clean(s.group(2)), "topics": []}
            units.append(unit)
            level = None
            items = unit["topics"]
            continue

        if unit is None:
            continue

        if _ZP.match(ln):
            flush_item()
            level = "podstawowy"
            # "Zakres podstawowy. Uczeń <inline single requirement>."
            tail = ln.split("Uczeń", 1)[1].strip().lstrip(":").strip()
            if tail and not tail.endswith(":"):
                cur = {"code": f"{unit['code']}.1", "level": level, "statement": tail}
                flush_item()
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
                    cur = {"code": f"{unit['code']}.R1", "level": level, "statement": body}
                    flush_item()
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
            flush_item()
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
    return units


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
        "# STATUS: DRAFT — every node must be verified against the Dz.U. text",
        "#   before M1 seeds from this file.",
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
            L.append(f"        statement: {_q(t['statement'])}")
            for sp in t.get("subpoints", []):
                L.append(f"        # {sp['code']}: {sp['statement']}")
    L.append("")
    return "\n".join(L)


def _q(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def run() -> int:
    units = parse()
    OUT_YAML.parent.mkdir(exist_ok=True)
    OUT_YAML.write_text(_yaml(units), encoding="utf-8")

    zp = sum(1 for u in units for t in u["topics"] if t["level"] == "podstawowy")
    zr = sum(1 for u in units for t in u["topics"] if t["level"] == "rozszerzony")
    subs = sum(len(t.get("subpoints", [])) for u in units for t in u["topics"])
    print(f"M0.6  {len(units)} units, {zp} podstawowy + {zr} rozszerzony topics, {subs} subpoints")
    for u in units:
        p = sum(1 for t in u["topics"] if t["level"] == "podstawowy")
        r = sum(1 for t in u["topics"] if t["level"] == "rozszerzony")
        print(f"      {u['code']:>4}. {u['name'][:44]:44} ZP {p:2}  ZR {r}")
    print(f"      wrote {OUT_YAML.relative_to(ROOT)}  (DRAFT — verify node by node)")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
