"""Thin pandoc wrapper: CKE accessibility DOCX -> LaTeX + extracted media.

Deterministic. No custom OMML handling; pandoc converts native OOXML maths to
LaTeX directly (SPEC section 2a, docs/decisions/0001-pandoc-over-custom-omml.md).

``--extract-media`` is always passed. Without it pandoc emits
``\\includegraphics{media/imageN.jpeg}`` for files it never writes (SPEC M0.2).
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path

PANDOC = "pandoc"


class PandocNotFound(RuntimeError):
    pass


class PandocConversionError(RuntimeError):
    pass


@dataclass(frozen=True)
class ConversionResult:
    docx: Path
    latex_path: Path
    media_dir: Path
    media_files: list[Path] = field(default_factory=list)
    stderr: str = ""

    @property
    def latex(self) -> str:
        return self.latex_path.read_text(encoding="utf-8")


def pandoc_version() -> str:
    try:
        out = subprocess.run(
            [PANDOC, "--version"], capture_output=True, text=True, check=True
        )
    except FileNotFoundError as exc:  # pragma: no cover - environment guard
        raise PandocNotFound("pandoc is not on PATH") from exc
    return out.stdout.splitlines()[0].strip()


def convert_docx_to_latex(docx: Path, out_dir: Path) -> ConversionResult:
    """Convert *docx* to LaTeX under *out_dir*.

    Writes ``<out_dir>/<stem>.tex`` and ``<out_dir>/media/``. ``--wrap=none``
    keeps each block on one logical line so the segmentation regexes in
    ``segment.py`` can anchor on line starts.
    """

    docx = Path(docx)
    out_dir = Path(out_dir)
    if not docx.is_file():
        raise FileNotFoundError(docx)
    out_dir.mkdir(parents=True, exist_ok=True)

    latex_path = out_dir / f"{docx.stem}.tex"
    media_dir = out_dir / "media"

    cmd = [
        PANDOC,
        str(docx),
        "--from=docx",
        "--to=latex",
        "--wrap=none",
        f"--extract-media={out_dir}",
        "--output",
        str(latex_path),
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True)
    except FileNotFoundError as exc:  # pragma: no cover - environment guard
        raise PandocNotFound("pandoc is not on PATH") from exc
    if proc.returncode != 0:
        raise PandocConversionError(proc.stderr.strip() or "pandoc failed")

    media_files = sorted(p for p in media_dir.rglob("*") if p.is_file())
    return ConversionResult(
        docx=docx,
        latex_path=latex_path,
        media_dir=media_dir,
        media_files=media_files,
        stderr=proc.stderr.strip(),
    )
