"""The deterministic Track A steps.

`segment_document` is the M0.2 wrapper unchanged in behaviour — convert, strip
boilerplate, segment on `Zadanie`, count `<w:drawing>` per task.
`validate_against_marking` is the hard gate: the segmented list must agree with
the `zasady oceniania` exactly. `run_pipeline` composes them for the job
handler; tests call the halves directly with synthetic input.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from zaspro.extraction.boilerplate import strip_boilerplate
from zaspro.extraction.figures import drawing_attribution
from zaspro.extraction.gate import cross_validate
from zaspro.extraction.marking_scheme import parse_marking_scheme
from zaspro.extraction.models import ExerciseChunk, MarkingSchemeTask, SegmentationGateResult
from zaspro.extraction.pandoc_convert import ConversionResult, convert_docx_to_latex
from zaspro.extraction.segment import segment_arkusz


class GateFailed(RuntimeError):
    """The segmented exercise list disagrees with the marking scheme."""


@dataclass
class SegmentedDocument:
    source_file: str
    conversion: ConversionResult
    body: str
    chunks: list[ExerciseChunk]
    figures_by_task: dict[str, int]
    figure_chrome: int
    figure_total: int
    ordered_numbers: list[str] = field(init=False)

    def __post_init__(self) -> None:
        self.ordered_numbers = [c.exercise_number for c in self.chunks]

    def next_number(self, number: str) -> str | None:
        try:
            i = self.ordered_numbers.index(number)
        except ValueError:
            return None
        return self.ordered_numbers[i + 1] if i + 1 < len(self.ordered_numbers) else None


@dataclass
class IngestionResult(SegmentedDocument):
    gate: SegmentationGateResult = None  # type: ignore[assignment]


def segment_document(docx: Path, work_dir: Path) -> SegmentedDocument:
    conv = convert_docx_to_latex(docx, work_dir)
    body, _strip = strip_boilerplate(conv.latex)
    figs_by_task, chrome, total = drawing_attribution(docx)
    chunks = segment_arkusz(body, source_document=docx.name, expected_figures=figs_by_task)
    return SegmentedDocument(
        source_file=docx.name,
        conversion=conv,
        body=body,
        chunks=chunks,
        figures_by_task={k: v for k, v in figs_by_task.items() if v},
        figure_chrome=chrome,
        figure_total=total,
    )


def validate_against_marking(
    seg: SegmentedDocument,
    marking_tasks: list[MarkingSchemeTask],
    *,
    marking_scheme: str,
    marking_scheme_is_deterministic: bool = False,
) -> SegmentationGateResult:
    gate = cross_validate(
        seg.chunks,
        marking_tasks,
        source_document=seg.source_file,
        marking_scheme=marking_scheme,
        marking_scheme_is_deterministic=marking_scheme_is_deterministic,
    )
    if not gate.passed:
        raise GateFailed(
            f"{seg.source_file} vs {marking_scheme}: "
            f"missing_in_arkusz={gate.missing_in_arkusz}, "
            f"missing_in_marking={gate.missing_in_marking}, "
            f"point_mismatches={gate.point_mismatches}, "
            f"tasks {gate.arkusz_task_count}/{gate.marking_task_count}, "
            f"points {gate.arkusz_points_total}/{gate.marking_points_total}"
        )
    return gate


def run_pipeline(
    docx: Path,
    marking_scheme_pdf: Path,
    work_dir: Path,
    *,
    marking_scheme_is_deterministic: bool = False,
) -> IngestionResult:
    seg = segment_document(docx, work_dir)
    gate = validate_against_marking(
        seg,
        parse_marking_scheme(marking_scheme_pdf),
        marking_scheme=marking_scheme_pdf.name,
        marking_scheme_is_deterministic=marking_scheme_is_deterministic,
    )
    return IngestionResult(
        source_file=seg.source_file,
        conversion=seg.conversion,
        body=seg.body,
        chunks=seg.chunks,
        figures_by_task=seg.figures_by_task,
        figure_chrome=seg.figure_chrome,
        figure_total=seg.figure_total,
        gate=gate,
    )
