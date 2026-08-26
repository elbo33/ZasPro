"""Build a tiny synthetic arkusz .docx in memory — no real source material.

Structure: cover boilerplate, then
    Zadanie 1. (0-1)           simple, 1 point
    Zadanie 2.                 parent (stem), no points
    Zadanie 2.1. (0-2)         subtask
    Zadanie 2.2. (0-1)         subtask
    Zadanie 3. (0-2)           simple, 2 points, carries one <w:drawing>
    Koniec
Total: 4 pointed leaf tasks, 6 points.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

_CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml"
    ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>
"""

_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1"
    Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument"
    Target="word/document.xml"/>
</Relationships>
"""

_DOC_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>
"""


def _p(*runs: str) -> str:
    inner = "".join(f'<w:r><w:t xml:space="preserve">{r}</w:t></w:r>' for r in runs)
    return f"<w:p>{inner}</w:p>"


def _p_drawing() -> str:
    return "<w:p><w:r><w:drawing></w:drawing></w:r></w:p>"


def _document_xml() -> str:
    body = "".join(
        [
            _p("Arkusz zawiera informacje prawnie chronione."),
            _p("Instrukcja dla zdajacego."),
            _p("Zadanie 1. (0–1)"),
            _p("Oblicz wartosc wyrazenia."),
            _p("Zadanie 2."),
            _p("Dana jest funkcja f. Wykres przedstawiono na rysunku."),
            _p("Zadanie 2.1. (0–2)"),
            _p("Podaj dziedzine funkcji f."),
            _p("Zadanie 2.2. (0–1)"),
            _p("Podaj zbior wartosci funkcji f."),
            _p("Zadanie 3. (0–2)"),
            _p("Na rysunku przedstawiono trojkat. Oblicz jego pole."),
            _p_drawing(),
            _p("Koniec"),
        ]
    )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<w:document xmlns:w="{_W}"><w:body>{body}'
        '<w:sectPr/></w:body></w:document>'
    )


def build_mini_arkusz_docx(path: Path) -> Path:
    path = Path(path)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", _CONTENT_TYPES)
        z.writestr("_rels/.rels", _RELS)
        z.writestr("word/_rels/document.xml.rels", _DOC_RELS)
        z.writestr("word/document.xml", _document_xml())
    return path
