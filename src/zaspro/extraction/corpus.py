"""M0.1 corpus split: which documents are Track A, with OOXML measurements.

Track A (SPEC M0): any CKE document with a ``_660.docx`` structured sibling,
convertible deterministically by pandoc. Track B: unstructured sources
(podstawa programowa, future textbooks), deferred.
"""

from __future__ import annotations

import re
import zipfile
from pathlib import Path

from .models import CorpusEntry, Track

_OMATH = re.compile(r"<m:oMath[ >]")
_OMATH_PARA = re.compile(r"<m:oMathPara[ >]")
_DRAWING = re.compile(r"<w:drawing[ >]")


def _manifest_rows(manifest_md: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    header: list[str] | None = None
    for line in manifest_md.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if header is None:
            header = cells
            continue
        if set("".join(cells)) <= {"-", ":", " "}:  # the |---|---| separator
            continue
        rows.append(dict(zip(header, cells)))
    return rows


def _has_660_token(filename: str) -> bool:
    """True if ``660`` appears as one of the dash-delimited paper codes in the
    name. For older sessions CKE ships a single zasady PDF whose name
    concatenates every variant, e.g.
    ``MMAP-P0-100-200-300-400-660-700-Q00-2209-zasady.pdf`` — the ``660`` token
    is the reliable signal that a czarnodruk export exists for that session,
    even when the index page does not link it (MANIFEST note, 27 Aug 2026)."""

    return "660" in filename.split("-")


def _mmap_session(filename: str) -> str | None:
    m = re.search(r"-(\d{4})-(?:zasady|arkusz)\b|-(\d{4})\.docx$", filename)
    return next((g for g in (m.groups() if m else ()) if g), None)


def _derive_sibling(filename: str) -> str | None:
    """Expected ``_660.docx`` sibling name for a standard-variant document."""

    if filename.endswith(".docx"):
        return None
    # zasady PDF carrying a 660 token -> the session has a czarnodruk arkusz.
    # Its own name is one of two conventions; report whichever is real.
    if filename.endswith("-zasady.pdf") and _has_660_token(filename):
        m = re.match(r"^(MMAP-[PR]0)-", filename)
        session = _mmap_session(filename)
        if m and session:
            return f"{m.group(1)}-660-{session}.docx"
    if "-100-" in filename:  # MMAP arkusze / zasady: -100- -> -660-
        return re.sub(r"\.pdf$", ".docx", filename.replace("-100-", "-660-"))
    if filename.endswith(".pdf"):  # informator convention: <stem>.pdf -> <stem>_660.docx
        return filename[:-4] + "_660.docx"
    return None


def _ooxml_counts(docx: Path) -> tuple[int, int, int, int]:
    with zipfile.ZipFile(docx) as zf:
        names = zf.namelist()
        media = sum(1 for n in names if n.startswith("word/media/"))
        xml = ""
        for part in ("word/document.xml", "word/document2.xml"):
            if part in names:
                xml += zf.read(part).decode("utf-8", "replace")
    return (
        len(_OMATH.findall(xml)),
        len(_OMATH_PARA.findall(xml)),
        len(_DRAWING.findall(xml)),
        media,
    )


def _classify(row: dict[str, str], sibling_present: bool, sibling_in_manifest: bool) -> tuple[Track, str | None]:
    fmt = row["format"].lower()
    stype = row["source_type"].upper()

    if fmt == "docx":
        return Track.A, None
    if stype == "PODSTAWA_PROGRAMOWA":
        return Track.B, "unstructured regulation; Track B (deferred, see docs/sources.md Part B)"
    if stype == "MARKING_SCHEME":
        note = (
            "PDF only — CKE publishes -zasady as PDF (docs/sources.md A3). "
            "Consumed deterministically via pdftotext as the M0.2 gate oracle. "
            "EXPLICIT EXCEPTION to the DOCX-sibling rule."
        )
        if _has_660_token(row["file"]):
            note += (
                " Name carries a 660 token -> a czarnodruk arkusz exists for "
                "this session (used for Track A ingestion even where the index "
                "page omits the link)."
            )
        return Track.A, note
    if sibling_present or sibling_in_manifest:
        return Track.A, "extraction source is its _660.docx sibling"
    if stype == "FORMULA_SHEET":
        return Track.NA, "no DOCX sibling; not exercise-bearing; revisit if formula extraction needs it"
    return Track.NA, "no DOCX sibling identified"


def build_corpus_split(manifest_md: Path, raw_dir: Path) -> list[CorpusEntry]:
    rows = _manifest_rows(Path(manifest_md))
    manifest_files = {r["file"] for r in rows}
    entries: list[CorpusEntry] = []

    for row in rows:
        filename = row["file"]
        fmt = row["format"].lower()
        sibling = _derive_sibling(filename)
        # a session's czarnodruk DOCX uses one of two namings; accept either
        alt = (
            re.sub(r"-660-(\d{4})\.docx$", r"-660-A-\1-arkusz.docx", sibling)
            if sibling
            else None
        )
        sibling_present = bool(sibling) and (
            (Path(raw_dir) / sibling).is_file()
            or (alt is not None and (Path(raw_dir) / alt).is_file())
        )
        sibling_in_manifest = bool(sibling) and (
            sibling in manifest_files or (alt is not None and alt in manifest_files)
        )

        track, note = _classify(row, sibling_present, sibling_in_manifest)

        omath = omath_para = drawings = media = None
        if fmt == "docx":
            path = Path(raw_dir) / filename
            if path.is_file():
                omath, omath_para, drawings, media = _ooxml_counts(path)
            else:
                note = f"declared in manifest but absent from {raw_dir}"

        entries.append(
            CorpusEntry(
                file=filename,
                title=row["title"],
                source_type=row["source_type"],
                fmt=fmt,
                track=track,
                docx_sibling=sibling if fmt != "docx" else None,
                sibling_present=sibling_present,
                omath=omath,
                omath_para=omath_para,
                drawings=drawings,
                media_files=media,
                notes=note,
            )
        )
    return entries
