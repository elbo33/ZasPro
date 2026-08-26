"""Typed boundaries for the Track A extraction pipeline.

These Pydantic models are the only shapes that cross module lines in M0. They
mirror a subset of the SPEC section 5 data model, but M0 serialises them to
JSONL on disk rather than to Postgres (schema and migrations are M1). See
docs/decisions/0004-m0-outputs-are-files-not-db.md.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, model_validator


class Track(str, Enum):
    """Corpus split from SPEC M0.1."""

    A = "A"  # structured CKE DOCX, deterministic pandoc conversion
    B = "B"  # unstructured (podstawa programowa, textbooks); deferred
    NA = "N/A"  # neither applies (e.g. the formula sheet as a standalone PDF)


class ExtractionMethod(str, Enum):
    """SPEC section 5: source_chunks.extraction_method."""

    pandoc_omml = "pandoc_omml"
    pdf_text = "pdf_text"
    pdf_vision = "pdf_vision"
    manual = "manual"


class CorpusEntry(BaseModel):
    """One row of the M0.1 corpus split table.

    ``omath`` / ``drawings`` / ``media_files`` are populated only for DOCX
    documents (they come from the OOXML package); for PDFs they stay ``None``.
    """

    file: str
    title: str
    source_type: str
    fmt: str  # "pdf" | "docx"
    track: Track

    # Structured-sibling analysis (SPEC M0.1: "has DOCX sibling").
    docx_sibling: str | None = None
    sibling_present: bool = False

    # OOXML measurements — DOCX only.
    omath: int | None = None
    omath_para: int | None = None  # display equations (<m:oMathPara>)
    drawings: int | None = None
    media_files: int | None = None

    notes: str | None = None


class ExerciseChunk(BaseModel):
    """One logical task extracted from a segmented arkusz.

    A parent (``is_parent=True``) carries the shared stem and has no points.
    Every subtask copies its parent's stem into ``stem_latex_raw`` so a reader
    of the JSONL never sees a subtask in isolation (SPEC section 5).
    """

    source_document: str
    order_index: int

    exercise_number: str  # "7", "12", "12.1"
    parent_number: str | None = None  # "12" for "12.1"; None otherwise
    is_parent: bool = False

    points_available: int | None = None  # None iff is_parent

    statement_latex_raw: str  # verbatim pandoc LaTeX for this task's body
    stem_latex_raw: str | None = None  # parent stem, attached to every child

    media_refs: list[str] = Field(default_factory=list)
    # <w:drawing> elements in this task's DOCX range. Pandoc drops Word-drawn
    # shapes silently, so expected > extracted means a figure was lost.
    expected_figure_count: int = 0

    extraction_method: ExtractionMethod = ExtractionMethod.pandoc_omml
    confidence: float | None = None  # None == deterministic, no review needed

    @model_validator(mode="after")
    def _check_points_vs_parent(self) -> ExerciseChunk:
        if self.is_parent and self.points_available is not None:
            raise ValueError(
                f"{self.exercise_number}: parent tasks carry no point value"
            )
        if not self.is_parent and self.points_available is None:
            raise ValueError(
                f"{self.exercise_number}: non-parent task is missing a point value"
            )
        if self.parent_number is not None and not self.exercise_number.startswith(
            self.parent_number + "."
        ):
            raise ValueError(
                f"{self.exercise_number}: parent_number {self.parent_number!r} "
                "is not a prefix of the exercise number"
            )
        return self

    @property
    def figures_incomplete(self) -> bool:
        """A figure the source carried was not extracted (SPEC: a data error)."""

        return self.expected_figure_count > len(self.media_refs)


class MarkingSchemeTask(BaseModel):
    """One task as independently enumerated by the zasady oceniania."""

    exercise_number: str
    points_available: int


class SegmentationGateResult(BaseModel):
    """Outcome of cross-validating a segmented arkusz against its marking scheme.

    SPEC M0.2: "Counts and point values must match exactly. This is a hard
    gate, not a report line."
    """

    source_document: str
    marking_scheme: str
    marking_scheme_is_deterministic: bool  # False => extracted from PDF (exception)

    arkusz_task_count: int
    marking_task_count: int
    arkusz_points_total: int
    marking_points_total: int

    missing_in_arkusz: list[str] = Field(default_factory=list)
    missing_in_marking: list[str] = Field(default_factory=list)
    point_mismatches: list[tuple[str, int, int]] = Field(default_factory=list)

    @property
    def passed(self) -> bool:
        return (
            not self.missing_in_arkusz
            and not self.missing_in_marking
            and not self.point_mismatches
            and self.arkusz_task_count == self.marking_task_count
            and self.arkusz_points_total == self.marking_points_total
        )
