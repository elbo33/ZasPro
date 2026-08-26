"""Job handlers for Track A ingestion.

INGEST_DOCUMENT runs the deterministic pipeline (a hard gate — a marking-scheme
mismatch fails the job) and enqueues one RENDER_VECTOR_FIGURE per figure-bearing
task. Figure rendering is separate because LibreOffice is slow and fails
independently; a lost figure leaves its exercise visibly incomplete
(`expected_figure_count > linked figures`), never silently empty.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from zaspro.db.models import (
    Exercise,
    ExerciseFigure,
    Figure,
    Job,
    JobType,
    RenderStatus,
    SourceDocument,
    SourceFormat,
)
from zaspro.extraction.figures_render import crop_task_figure, docx_to_pdf, task_page_map
from zaspro.extraction.marking_scheme import parse_marking_scheme
from zaspro.extraction.models import MarkingSchemeTask
from zaspro.ingestion.pipeline import (
    IngestionResult,
    segment_document,
    validate_against_marking,
)
from zaspro.ingestion.persist import persist_ingestion
from zaspro.jobs import enqueue, register
from zaspro.storage import get_storage

RAW = Path(__file__).resolve().parents[3] / "sources" / "raw"


def _resolve(ref: str) -> Path:
    """A bare filename resolves under sources/raw/; an absolute path is used as-is
    (tests pass a tmp-dir DOCX)."""

    p = Path(ref)
    return p if p.is_absolute() else RAW / ref


@register(JobType.INGEST_DOCUMENT)
def handle_ingest_document(session: Session, job: Job) -> dict:
    payload = job.input
    docx = _resolve(payload["source_file_ref"])
    if not docx.is_file():
        raise FileNotFoundError(docx)

    # Marking scheme: a structured list in the payload, else parse the PDF.
    if payload.get("marking_tasks") is not None:
        marking_tasks = [MarkingSchemeTask(**t) for t in payload["marking_tasks"]]
        marking_name = payload.get("marking_scheme_file_ref", "payload")
        marking_deterministic = True
    else:
        marking_pdf = _resolve(payload["marking_scheme_file_ref"])
        if not marking_pdf.is_file():
            raise FileNotFoundError(marking_pdf)
        marking_tasks = parse_marking_scheme(marking_pdf)
        marking_name = marking_pdf.name
        marking_deterministic = False

    storage = get_storage()
    with tempfile.TemporaryDirectory() as td:
        work = Path(td)
        seg = segment_document(docx, work / "convert")
        gate = validate_against_marking(
            seg, marking_tasks,
            marking_scheme=marking_name,
            marking_scheme_is_deterministic=marking_deterministic,
        )
        result = IngestionResult(
            source_file=seg.source_file, conversion=seg.conversion, body=seg.body,
            chunks=seg.chunks, figures_by_task=seg.figures_by_task,
            figure_chrome=seg.figure_chrome, figure_total=seg.figure_total, gate=gate,
        )
        doc = persist_ingestion(session, result)

        pdf = docx_to_pdf(docx, work / "pdf")
        doc.page_count = _pdf_pages(pdf)
        pdf_key = f"ingest/{doc.id}/render.pdf"
        storage.put(pdf_key, pdf.read_bytes())

    figure_jobs = 0
    for number in sorted(result.figures_by_task, key=lambda n: [int(x) for x in n.split(".")]):
        enqueue(
            session,
            JobType.RENDER_VECTOR_FIGURE,
            {
                "source_document_id": doc.id,
                "exercise_number": number,
                "next_number": result.next_number(number),
                "pdf_key": pdf_key,
            },
        )
        figure_jobs += 1

    return {
        "source_document_id": doc.id,
        "gate": "pass",
        "tasks": result.gate.arkusz_task_count,
        "points": result.gate.arkusz_points_total,
        "chunks": len(result.chunks),
        "exercises": len(result.chunks),
        "figure_jobs": figure_jobs,
    }


@register(JobType.RENDER_VECTOR_FIGURE)
def handle_render_vector_figure(session: Session, job: Job) -> dict:
    p = job.input
    doc_id = p["source_document_id"]
    number = p["exercise_number"]
    doc = session.get(SourceDocument, doc_id)
    if doc is None:
        raise RuntimeError(f"source_document {doc_id} gone")

    storage = get_storage()
    with tempfile.TemporaryDirectory() as td:
        pdf_path = Path(td) / "render.pdf"
        pdf_path.write_bytes(storage.get(p["pdf_key"]))
        lookup = [number] + ([p["next_number"]] if p["next_number"] else [])
        pages = task_page_map(pdf_path, lookup)
        page = pages.get(number)
        if page is None:
            raise RuntimeError(f"Zadanie {number} marker not found in the rendered PDF")
        out_png = Path(td) / f"{number}.png"
        crop = crop_task_figure(
            pdf_path, page, number, out_png, next_task=p["next_number"]
        )
        key = f"figures/{doc_id}/{number}.png"
        storage.put_file(key, out_png)

    figure = Figure(
        source_document_id=doc_id,
        page=crop.page,
        bbox=",".join(f"{v:.0f}" for v in crop.bbox),
        image_ref=key,
        source_format=SourceFormat.WORD_SHAPE,
        render_status=RenderStatus.COMPLETE,
        caption=None,
    )
    session.add(figure)
    session.flush()

    # link to the task and, if it is a parent, to its subtasks (SPEC §5:
    # a figure can serve several subtasks)
    targets = session.scalars(
        select(Exercise).where(
            Exercise.source_document_id == doc_id,
            (Exercise.exercise_number == number)
            | (Exercise.exercise_number.like(f"{number}.%")),
        )
    ).all()
    for ex in targets:
        session.add(ExerciseFigure(exercise_id=ex.id, figure_id=figure.id))
    session.flush()

    return {
        "figure_id": figure.id,
        "image_ref": key,
        "warnings": crop.warnings,
        "linked_exercises": [ex.exercise_number for ex in targets],
    }


def _pdf_pages(pdf: Path) -> int | None:
    import subprocess

    try:
        out = subprocess.run(
            ["pdfinfo", str(pdf)], capture_output=True, text=True, check=True
        ).stdout
    except Exception:  # noqa: BLE001
        return None
    import re

    m = re.search(r"^Pages:\s+(\d+)", out, re.MULTILINE)
    return int(m.group(1)) if m else None
