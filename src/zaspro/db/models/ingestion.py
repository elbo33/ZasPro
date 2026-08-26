"""Ingestion tables (SPEC §5): source_documents, source_chunks, figures.

`source_chunks.confidence` is nullable with **no default**. NULL means
"deterministically extracted, no confidence to record" — pandoc conversion has
none. Review triage (M3) treats NULL as trustworthy and keeps those chunks out
of the queue (SPEC §5, §9). A NOT NULL or a default here would undo that.
"""

from __future__ import annotations

import enum

from sqlalchemy import Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from zaspro.db.base import Base, TimestampMixin


class ExtractionStatus(str, enum.Enum):
    PENDING = "pending"
    CONVERTED = "converted"
    SEGMENTED = "segmented"
    VALIDATED = "validated"
    FAILED = "failed"


class ContentType(str, enum.Enum):
    EXPLANATION = "EXPLANATION"
    DEFINITION = "DEFINITION"
    FORMULA = "FORMULA"
    EXAMPLE = "EXAMPLE"
    EXERCISE = "EXERCISE"
    SOLUTION = "SOLUTION"
    THEOREM = "THEOREM"
    NOTE = "NOTE"
    WARNING = "WARNING"


class ExtractionMethod(str, enum.Enum):
    pandoc_omml = "pandoc_omml"
    pdf_text = "pdf_text"
    pdf_vision = "pdf_vision"
    manual = "manual"


class SourceFormat(str, enum.Enum):
    RASTER = "RASTER"
    WMF = "WMF"
    WORD_SHAPE = "WORD_SHAPE"


class RenderStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETE = "complete"
    FAILED = "failed"


def _enum(py_enum: type[enum.Enum], name: str) -> Enum:
    return Enum(py_enum, name=name, native_enum=False, validate_strings=True)


class SourceDocument(Base, TimestampMixin):
    __tablename__ = "source_documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id", ondelete="CASCADE"))
    file_ref: Mapped[str] = mapped_column(String(255), unique=True)
    page_count: Mapped[int | None] = mapped_column(Integer)
    extraction_status: Mapped[ExtractionStatus] = mapped_column(
        _enum(ExtractionStatus, "extraction_status"), default=ExtractionStatus.PENDING
    )
    variant_code: Mapped[str | None] = mapped_column(String(8))  # 100 | 200 | 660 | 700
    paper_version: Mapped[str | None] = mapped_column(String(2))  # A | B
    session_code: Mapped[str | None] = mapped_column(String(16))  # e.g. 2605
    # Where the text actually came from, when this document's counterpart is a
    # different file (the 660 DOCX feeding a 100 PDF exercise). SPEC §5.
    sibling_docx_ref: Mapped[str | None] = mapped_column(String(255))

    chunks: Mapped[list[SourceChunk]] = relationship(
        back_populates="document", cascade="all, delete-orphan", order_by="SourceChunk.order_index"
    )
    figures: Mapped[list[Figure]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )


class SourceChunk(Base):
    __tablename__ = "source_chunks"
    __table_args__ = (
        UniqueConstraint("source_document_id", "order_index", name="uq_source_chunks_doc_order"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source_document_id: Mapped[int] = mapped_column(
        ForeignKey("source_documents.id", ondelete="CASCADE")
    )
    page: Mapped[int | None] = mapped_column(Integer)
    chapter: Mapped[str | None] = mapped_column(String(255))
    section: Mapped[str | None] = mapped_column(String(255))
    heading: Mapped[str | None] = mapped_column(String(255))
    content_type: Mapped[ContentType] = mapped_column(_enum(ContentType, "content_type"))
    text: Mapped[str] = mapped_column(Text)
    latex: Mapped[str | None] = mapped_column(Text)  # raw, for display
    order_index: Mapped[int] = mapped_column(Integer)
    extraction_method: Mapped[ExtractionMethod] = mapped_column(
        _enum(ExtractionMethod, "extraction_method")
    )
    # NULL == deterministic (see module docstring). No default on purpose.
    confidence: Mapped[float | None] = mapped_column()

    document: Mapped[SourceDocument] = relationship(back_populates="chunks")


class Figure(Base):
    __tablename__ = "figures"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_document_id: Mapped[int] = mapped_column(
        ForeignKey("source_documents.id", ondelete="CASCADE")
    )
    page: Mapped[int | None] = mapped_column(Integer)
    bbox: Mapped[str | None] = mapped_column(String(120))  # "x0,y0,x1,y1" in PDF points
    image_ref: Mapped[str | None] = mapped_column(Text)  # storage key
    source_format: Mapped[SourceFormat] = mapped_column(_enum(SourceFormat, "source_format"))
    render_status: Mapped[RenderStatus] = mapped_column(
        _enum(RenderStatus, "render_status"), default=RenderStatus.PENDING
    )
    caption: Mapped[str | None] = mapped_column(Text)

    document: Mapped[SourceDocument] = relationship(back_populates="figures")
