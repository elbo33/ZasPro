"""Batch-ingest the Track A corpus and summarise it.

Track A = CKE exam papers with a `_660.docx` czarnodruk (podstawowy, version A
only — see sources/MANIFEST.md). Their marking schemes are PDF; the file name
convention moves between years, so resolution tries both the czarnodruk and the
standard name for the session.

Track B (rozszerzony everything, version B papers) is registered in
`source_documents` but not ingested (ADR 0005).

The informatory are not `Zadanie` lists — they get a structural audit here, not
an ingest; their semantic chunking is separate work.
"""

from __future__ import annotations

import re
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

import zaspro.ingestion.handlers  # noqa: F401 - register job handlers
from zaspro.db.models import (
    ExtractionStatus,
    Job,
    JobStatus,
    JobType,
    Source,
    SourceDocument,
)
from zaspro.extraction.figures import drawing_attribution
from zaspro.extraction.pandoc_convert import convert_docx_to_latex
from zaspro.ingestion.report import IngestionReport, build_report
from zaspro.jobs import Worker, enqueue

ROOT = Path(__file__).resolve().parents[3]
RAW = ROOT / "sources" / "raw"
OUT = ROOT / "m2"

# Two czarnodruk DOCX naming conventions in the corpus (sources/MANIFEST.md
# note, 27 Aug 2026):
#   MMAP-P0-660-A-2405-arkusz.docx   sessions whose PDF keeps the -A/-B letter
#   MMAP-P0-660-2305.docx            older sessions that drop the letter (no
#                                    version, no "-arkusz" suffix)
# A missing letter means paper_version is unknown, not "A".
_ARKUSZ = re.compile(r"^MMAP-([PR]0)-(\d{3})-(?:([AB])-)?(\d{4})(?:-arkusz)?\.docx$")


def arkusz_session(file_ref: str) -> str | None:
    m = _ARKUSZ.match(file_ref)
    return m.group(4) if m else None


def resolve_marking_scheme(arkusz_file_ref: str, raw: Path = RAW) -> str | None:
    m = _ARKUSZ.match(arkusz_file_ref)
    if not m:
        return None
    level, _variant, _version, session = m.groups()
    for candidate in (
        f"MMAP-{level}-660-{session}-zasady.pdf",  # czarnodruk, matches the DOCX
        f"MMAP-{level}-100-{session}-zasady.pdf",  # standard
    ):
        if (raw / candidate).is_file():
            return candidate
    # Older sessions ship one zasady PDF whose name concatenates every paper
    # code for the session, e.g.
    #   MMAP-P0-100-200-300-400-660-700-Q00-2209-zasady.pdf
    # The "660" token in that name is the reliable signal that a czarnodruk
    # exists for the session (MANIFEST note). Prefer such a file.
    globbed = sorted(p.name for p in raw.glob(f"MMAP-{level}-*-{session}-zasady.pdf"))
    for name in globbed:
        if "-660-" in name:
            return name
    return globbed[0] if globbed else None


@dataclass
class DocResult:
    file: str
    session: str
    outcome: str  # "pass" | "gate-fail" | "error" | "no-marking-scheme"
    marking_scheme: str | None = None
    reason: str | None = None
    report: IngestionReport | None = None


@dataclass
class InformatorAudit:
    file: str
    omath: int
    omath_para: int
    drawings: int
    zadanie_markers: int
    przyklad_markers: int


@dataclass
class BatchSummary:
    docs: list[DocResult] = field(default_factory=list)
    informatory: list[InformatorAudit] = field(default_factory=list)
    track_b_registered: list[str] = field(default_factory=list)

    @property
    def all_passed(self) -> bool:
        return bool(self.docs) and all(d.outcome == "pass" for d in self.docs)


def _ingest_one(session: Session, arkusz: str, marking: str) -> DocResult:
    session_code = arkusz_session(arkusz) or "?"
    job = enqueue(session, JobType.INGEST_DOCUMENT, {
        "source_file_ref": arkusz, "marking_scheme_file_ref": marking,
    })
    session.commit()
    Worker().drain()
    session.expire_all()

    j = session.get(Job, job.id)
    if j.status is not JobStatus.SUCCEEDED:
        reason = (j.error or "").strip().splitlines()[-1] if j.error else "unknown"
        outcome = "gate-fail" if "GateFailed" in (j.error or "") else "error"
        return DocResult(arkusz, session_code, outcome, marking, reason=reason)

    failed_renders = session.scalars(
        select(Job).where(
            Job.job_type == JobType.RENDER_VECTOR_FIGURE, Job.status == JobStatus.FAILED
        )
    ).all()
    rep = build_report(session, j.output["source_document_id"])
    if not rep.figures_ok:
        return DocResult(
            arkusz, session_code, "error", marking, report=rep,
            reason=f"{len(failed_renders)} figure render(s) failed; incomplete={rep.incomplete}",
        )
    return DocResult(arkusz, session_code, "pass", marking, report=rep)


def _audit_informator(docx: Path) -> InformatorAudit:
    import zipfile

    with tempfile.TemporaryDirectory() as td:
        tex = convert_docx_to_latex(docx, Path(td)).latex
    _by_task, _chrome, total_drawings = drawing_attribution(docx)
    with zipfile.ZipFile(docx) as z:
        xml = z.read("word/document.xml").decode("utf-8", "replace")
    return InformatorAudit(
        file=docx.name,
        omath=len(re.findall(r"<m:oMath[ >]", xml)),
        omath_para=len(re.findall(r"<m:oMathPara[ >]", xml)),
        drawings=total_drawings,
        zadanie_markers=len(re.findall(r"(?m)^Zadanie\s+\d+\.", tex)),
        przyklad_markers=len(re.findall(r"(?mi)^Przykład\s+\d+", tex)),
    )


def _register_track_b(session: Session) -> list[str]:
    """Bare source_documents for every EXAM/MARKING_SCHEME source not yet
    ingested. Track B stays deferred (ADR 0005)."""

    registered: list[str] = []
    exam_sources = session.scalars(
        select(Source).where(Source.source_type.in_(["EXAM", "MARKING_SCHEME"]))
    ).all()
    for src in exam_sources:
        # a Track A czarnodruk arkusz that failed its gate is *attempted*, not
        # deferred — don't file it under Track B
        if _ARKUSZ.match(src.file_ref):
            continue
        existing = session.scalars(
            select(SourceDocument).where(SourceDocument.file_ref == src.file_ref)
        ).one_or_none()
        if existing is not None:
            continue
        m = re.match(r"^MMAP-([PR]0)-(\d{3})-(?:([AB])-)?(\d{4})-", src.file_ref)
        session.add(SourceDocument(
            source_id=src.id,
            file_ref=src.file_ref,
            extraction_status=ExtractionStatus.PENDING,
            variant_code=m.group(2) if m else None,
            paper_version=m.group(3) if m else None,
            session_code=m.group(4) if m else None,
        ))
        registered.append(src.file_ref)
    session.flush()
    return registered


def run(session: Session) -> BatchSummary:
    summary = BatchSummary()

    track_a = session.scalars(
        select(Source).where(Source.source_type == "EXAM", Source.file_ref.like("%.docx"))
    ).all()
    for src in sorted(track_a, key=lambda s: s.file_ref):
        marking = resolve_marking_scheme(src.file_ref)
        if marking is None:
            summary.docs.append(DocResult(
                src.file_ref, arkusz_session(src.file_ref) or "?",
                "no-marking-scheme", reason="no zasady PDF found for this session",
            ))
            continue
        summary.docs.append(_ingest_one(session, src.file_ref, marking))

    for src in session.scalars(
        select(Source).where(
            Source.source_type == "OFFICIAL_CKE", Source.file_ref.like("Informator%.docx")
        )
    ):
        summary.informatory.append(_audit_informator(RAW / src.file_ref))

    summary.track_b_registered = _register_track_b(session)
    session.commit()
    return summary
