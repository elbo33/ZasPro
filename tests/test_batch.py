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

    # 7/7 pass, after: two parser fixes (naming, multi-variant zasady), one
    # hand-entered marking-scheme correction (2209/10.3, source defect), and
    # three hand-entered non-figure records (2209/10.1, 2312/11.4, 2605/32).
    assert {s for s, d in by_session.items() if d.outcome == "pass"} == set(by_session)
    points = {s: by_session[s].report.points_total for s in by_session}
    assert points == {
        "2203": 46, "2209": 46, "2305": 46, "2312": 46,
        "2405": 46, "2505": 50, "2605": 50,
    }

    # the 2209 marking-scheme override supplied the point value the PDF omits
    assert by_session["2209"].report.leaf_tasks == 35

    from zaspro.db.models import SourceDocument

    validated = {
        d.session_code
        for d in db.query(SourceDocument).filter(
            SourceDocument.extraction_status == "validated"
        )
    }
    assert validated == {"2203", "2209", "2305", "2312", "2405", "2505", "2605"}

    # a Track A czarnodruk is never filed under Track B
    assert not any(
        f.startswith("MMAP-P0-660-") and f.endswith(".docx")
        for f in summary.track_b_registered
    )

    # informatory audited, not ingested
    assert {a.file for a in summary.informatory} == {
        "Informator_EM2024_matematyka_pp_660.docx",
        "Informator_EM2024_matematyka_pr_660.docx",
    }
    assert not db.query(SourceDocument).filter(
        SourceDocument.file_ref.like("Informator%")
    ).count()


def test_figure_overrides_zero_the_stray_drawings(db):
    """The three hand-recorded non-figure drawings drop out of the per-task
    counts (sources/figure_overrides.yaml)."""
    from zaspro.extraction.figures import count_drawings_by_task

    assert (RAW / "MMAP-P0-660-A-2312-arkusz.docx").is_file()
    c2312 = count_drawings_by_task(RAW / "MMAP-P0-660-A-2312-arkusz.docx")
    assert c2312.get("11.4", 0) == 0
    c2605 = count_drawings_by_task(RAW / "MMAP-P0-660-A-2605-arkusz.docx")
    assert c2605.get("32", 0) == 0
    c2209 = count_drawings_by_task(RAW / "MMAP-P0-660-2209.docx")
    assert c2209.get("10.1", 0) == 0
