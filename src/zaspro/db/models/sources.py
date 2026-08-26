"""`sources` table (SPEC §5). Seeded verbatim from `sources/MANIFEST.md`.

SPEC M1: "Do not have a model generate or infer licensing metadata; it comes
from the manifest, which is authored by hand." The enums here match the
manifest's vocabulary exactly, so an unrecognised value fails loudly at seed
time rather than being silently coerced.

Document-level attributes (variant, session, paper version, sibling DOCX) go in
`source_documents` in M2; for M1 they are carried along in `notes`.
"""

from __future__ import annotations

import enum

from sqlalchemy import Enum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from zaspro.db.base import Base, ShortName, TimestampMixin


class SourceType(str, enum.Enum):
    PODSTAWA_PROGRAMOWA = "PODSTAWA_PROGRAMOWA"
    OFFICIAL_CKE = "OFFICIAL_CKE"
    EXAM = "EXAM"
    MARKING_SCHEME = "MARKING_SCHEME"
    FORMULA_SHEET = "FORMULA_SHEET"
    TEXTBOOK = "TEXTBOOK"
    OPEN_EDUCATIONAL_RESOURCE = "OPEN_EDUCATIONAL_RESOURCE"
    USER_PROVIDED = "USER_PROVIDED"
    OTHER = "OTHER"


class LicenceStatus(str, enum.Enum):
    # Exactly the values defined in sources/MANIFEST.md.
    MATERIAL_URZEDOWY = "MATERIAL_URZEDOWY"
    CKE_UNSPECIFIED = "CKE_UNSPECIFIED"


class ProcessingStatus(str, enum.Enum):
    PENDING = "pending"
    INGESTED = "ingested"
    FAILED = "failed"


def _enum(py_enum: type[enum.Enum], name: str) -> Enum:
    return Enum(py_enum, name=name, native_enum=False, validate_strings=True)


class Source(Base, TimestampMixin):
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(Text)
    author: Mapped[str | None] = mapped_column(String(255))
    publisher: Mapped[ShortName]
    year: Mapped[int | None] = mapped_column(Integer)
    source_type: Mapped[SourceType] = mapped_column(_enum(SourceType, "source_type"))
    licence_status: Mapped[LicenceStatus] = mapped_column(_enum(LicenceStatus, "licence_status"))
    verbatim_ok: Mapped[bool] = mapped_column(default=False)
    reuse_notes: Mapped[str | None] = mapped_column(Text)
    url: Mapped[str] = mapped_column(Text)
    # Natural key for idempotent seeding: the file name in sources/raw/.
    file_ref: Mapped[str] = mapped_column(String(255), unique=True)
    notes: Mapped[str | None] = mapped_column(Text)
    processing_status: Mapped[ProcessingStatus] = mapped_column(
        _enum(ProcessingStatus, "processing_status"), default=ProcessingStatus.PENDING
    )
