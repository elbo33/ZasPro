"""Parse `sources/MANIFEST.md` — the hand-authored source inventory.

Deterministic, no inference. The markdown table's columns map to `sources`
rows; `session` / `level` / `variant` / `paper_version` are document-level and
carried in `notes` until M2 gives them `source_documents` rows.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MANIFEST = ROOT / "sources" / "MANIFEST.md"


@dataclass(frozen=True)
class ManifestRow:
    file: str
    title: str
    publisher: str
    source_type: str
    session: str
    level: str
    variant: str
    paper_version: str
    url: str
    licence_status: str
    verbatim_ok: bool
    fmt: str

    @property
    def notes(self) -> str:
        parts = [f"format={self.fmt}"]
        for label, value in (
            ("session", self.session),
            ("level", self.level),
            ("variant", self.variant),
            ("paper_version", self.paper_version),
        ):
            if value and value.lower() not in {"n/a", "-", ""}:
                parts.append(f"{label}={value}")
        return "; ".join(parts)


def _table_rows(md: str) -> list[dict[str, str]]:
    header: list[str] | None = None
    rows: list[dict[str, str]] = []
    for line in md.splitlines():
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


def load_manifest(path: Path = MANIFEST) -> list[ManifestRow]:
    out: list[ManifestRow] = []
    for r in _table_rows(path.read_text(encoding="utf-8")):
        vok = r["verbatim_ok"].strip().lower()
        if vok not in {"true", "false"}:
            raise ValueError(f"{r['file']}: verbatim_ok must be true/false, got {r['verbatim_ok']!r}")
        out.append(
            ManifestRow(
                file=r["file"],
                title=r["title"],
                publisher=r["publisher"],
                source_type=r["source_type"],
                session=r["session"],
                level=r["level"],
                variant=r["variant"],
                paper_version=r["paper_version"],
                url=r["url"],
                licence_status=r["licence_status"],
                verbatim_ok=(vok == "true"),
                fmt=r["format"],
            )
        )
    if not out:
        raise ValueError(f"no rows parsed from {path}")
    return out
