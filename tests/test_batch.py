"""Track A batch: marking-scheme resolution (pure) and the corpus run (real)."""

import shutil
from pathlib import Path

import pytest

from tests.conftest import needs_pandoc, needs_soffice
from zaspro.ingestion.batch import RAW, arkusz_session, resolve_marking_scheme, run
from zaspro.ingestion.persist import _doc_metadata
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


# --- the no-version-letter DOCX naming (older sessions) ----------------------


def test_arkusz_regex_accepts_both_namings():
    # letter + "-arkusz" suffix
    assert arkusz_session("MMAP-P0-660-A-2405-arkusz.docx") == "2405"
    # no letter, no suffix (2203 / 2209 / 2305)
    assert arkusz_session("MMAP-P0-660-2305.docx") == "2305"
    assert arkusz_session("MMAP-P0-660-2209.docx") == "2209"
    assert arkusz_session("not-an-arkusz.docx") is None


def test_no_letter_naming_leaves_paper_version_null():
    letter = _doc_metadata("MMAP-P0-660-A-2312-arkusz.docx")
    assert (letter["session_code"], letter["paper_version"], letter["variant_code"]) == (
        "2312",
        "A",
        "660",
    )
    noletter = _doc_metadata("MMAP-P0-660-2305.docx")
    assert noletter["session_code"] == "2305"
    assert noletter["paper_version"] is None  # NOT defaulted to "A"
    assert noletter["variant_code"] == "660"


def test_resolves_multivariant_zasady_by_660_token(tmp_path):
    # older sessions: one concatenated-variant zasady PDF for the session
    (tmp_path / "MMAP-P0-100-200-300-400-660-700-Q00-2209-zasady.pdf").touch()
    assert (
        resolve_marking_scheme("MMAP-P0-660-2209.docx", tmp_path)
        == "MMAP-P0-100-200-300-400-660-700-Q00-2209-zasady.pdf"
    )


def test_exact_name_still_wins_over_multivariant(tmp_path):
    (tmp_path / "MMAP-P0-100-2305-zasady.pdf").touch()
    (tmp_path / "MMAP-P0-100-200-300-400-660-2305-zasady.pdf").touch()
    assert (
        resolve_marking_scheme("MMAP-P0-660-2305.docx", tmp_path)
        == "MMAP-P0-100-2305-zasady.pdf"
    )


# --- the corpus run ----------------------------------------------------------

_TRACK_A = [
    "MMAP-P0-660-2203.docx",
    "MMAP-P0-660-2209.docx",
    "MMAP-P0-660-2305.docx",
    "MMAP-P0-660-A-2312-arkusz.docx",
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
def test_track_a_corpus_seven_sessions(db):
    seed_sources(db)
    db.commit()

    summary = run(db)
    db.expire_all()

    by_session = {d.session: d for d in summary.docs}
    assert set(by_session) == {"2203", "2209", "2305", "2312", "2405", "2505", "2605"}

    # 5 pass clean
    passing = {s for s, d in by_session.items() if d.outcome == "pass"}
    assert passing == {"2203", "2305", "2405", "2505", "2605"}
    points = {s: by_session[s].report.points_total for s in passing}
    assert points == {"2203": 46, "2305": 46, "2405": 46, "2505": 50, "2605": 50}

    # 2209: source-PDF defect — one subtask's point range missing from the zasady
    d2209 = by_session["2209"]
    assert d2209.outcome == "gate-fail"
    assert "10.3" in d2209.reason

    # 2312: one task figure is raster/WMF, not a Word shape the crop can handle
    d2312 = by_session["2312"]
    assert d2312.outcome == "error"
    assert "11.4" in d2312.reason

    # a Track A czarnodruk that failed its gate is NOT filed under Track B
    assert not any(
        f.startswith("MMAP-P0-660-") and f.endswith(".docx")
        for f in summary.track_b_registered
    )

    from zaspro.db.models import SourceDocument

    validated = db.query(SourceDocument).filter(
        SourceDocument.extraction_status == "validated"
    ).all()
    # the 5 clean passes + 2312 (gate ok, only a later figure render failed)
    assert {d.session_code for d in validated} == {"2203", "2305", "2312", "2405", "2505", "2605"}

    # informatory audited, not ingested
    assert {a.file for a in summary.informatory} == {
        "Informator_EM2024_matematyka_pp_660.docx",
        "Informator_EM2024_matematyka_pr_660.docx",
    }
    assert not db.query(SourceDocument).filter(
        SourceDocument.file_ref.like("Informator%")
    ).count()
