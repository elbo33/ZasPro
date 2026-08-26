"""Track A batch: marking-scheme resolution (pure) and the corpus run (real)."""

import shutil
from pathlib import Path

import pytest

from tests.conftest import needs_pandoc, needs_soffice
from zaspro.ingestion.batch import RAW, resolve_marking_scheme, run
from zaspro.seeding.sources import seed_sources

# --- marking-scheme resolution -------------------------------------------------


def test_resolves_czarnodruk_then_standard(tmp_path):
    (tmp_path / "MMAP-P0-100-2505-zasady.pdf").touch()
    (tmp_path / "MMAP-P0-660-2505-zasady.pdf").touch()
    # 660 preferred when both exist
    assert (
        resolve_marking_scheme("MMAP-P0-660-A-2505-arkusz.docx", tmp_path)
        == "MMAP-P0-660-2505-zasady.pdf"
    )


def test_falls_back_to_standard_name(tmp_path):
    (tmp_path / "MMAP-P0-100-2405-zasady.pdf").touch()
    assert (
        resolve_marking_scheme("MMAP-P0-660-A-2405-arkusz.docx", tmp_path)
        == "MMAP-P0-100-2405-zasady.pdf"
    )


def test_drops_the_version_letter(tmp_path):
    (tmp_path / "MMAP-R0-100-2505-zasady.pdf").touch()
    assert (
        resolve_marking_scheme("MMAP-R0-100-B-2505-arkusz.docx", tmp_path)
        == "MMAP-R0-100-2505-zasady.pdf"
    )


def test_returns_none_when_absent(tmp_path):
    assert resolve_marking_scheme("MMAP-P0-660-A-9999-arkusz.docx", tmp_path) is None
    assert resolve_marking_scheme("not-an-arkusz.docx", tmp_path) is None


# --- the corpus run ----------------------------------------------------------

_TRACK_A = [
    "MMAP-P0-660-A-2405-arkusz.docx",
    "MMAP-P0-660-A-2505-arkusz.docx",
    "MMAP-P0-660-A-2605-arkusz.docx",
]

pytestmark_corpus = pytest.mark.skipif(
    not all((RAW / f).is_file() for f in _TRACK_A)
    or shutil.which("pdftotext") is None,
    reason="Track A corpus files or poppler not present",
)


@needs_pandoc
@needs_soffice
@pytestmark_corpus
def test_track_a_corpus_ingests_and_registers_track_b(db):
    seed_sources(db)
    db.commit()

    summary = run(db)
    db.expire_all()

    assert [d.outcome for d in summary.docs] == ["pass", "pass", "pass"]
    assert summary.all_passed

    points = {d.session: d.report.points_total for d in summary.docs}
    assert points == {"2405": 46, "2505": 50, "2605": 50}

    # 3 Track A documents validated, everything else registered but empty
    from zaspro.db.models import Exercise, SourceDocument

    docs = db.query(SourceDocument).all()
    validated = [d for d in docs if d.extraction_status.value == "validated"]
    pending = [d for d in docs if d.extraction_status.value == "pending"]
    assert len(validated) == 3
    assert len(pending) == len(summary.track_b_registered) == 13
    for d in pending:
        assert db.query(Exercise).filter_by(source_document_id=d.id).count() == 0

    # informatory audited, not ingested
    assert {a.file for a in summary.informatory} == {
        "Informator_EM2024_matematyka_pp_660.docx",
        "Informator_EM2024_matematyka_pr_660.docx",
    }
    assert not db.query(SourceDocument).filter(
        SourceDocument.file_ref.like("Informator%")
    ).count()
