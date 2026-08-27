"""exercise_topics materialisation (M4, ADR 0010)."""

from __future__ import annotations

from tests.fixtures.mapping_world import build_world
from zaspro.db.models import (
    ChunkMapping, ContentType, ExerciseTopic, ExtractionMethod, MappingStatus,
    SourceChunk, TopicRole,
)
from zaspro.knowledge.aggregate import rebuild_exercise_topics, topic_chunk_counts


def _map_row(db, w, chunk_id, topic_code, *, primary, status, conf=0.9):
    m = ChunkMapping(
        source_chunk_id=chunk_id, is_primary=primary,
        topic_id=w.topic_ids[topic_code], content_type=ContentType.EXERCISE,
        confidence=conf, mapping_status=status, prompt_version="m3-map-v2",
    )
    db.add(m)
    db.flush()
    return m


def test_rebuild_emits_primary_and_approved_secondary_rows(db):
    w = build_world(db)
    # chunk "1" -> Exercise "1"; give it a primary VIII.2 + secondary VIII.1
    _map_row(db, w, w.chunk_ids["1"], "VIII.2", primary=True, status=MappingStatus.AI_SUGGESTED)
    _map_row(db, w, w.chunk_ids["1"], "VIII.1", primary=False, status=MappingStatus.AI_SUGGESTED, conf=0.5)

    res = rebuild_exercise_topics(db)
    assert res.primary_rows == 1 and res.secondary_rows == 1

    rows = db.query(ExerciseTopic).all()
    roles = {r.topic_id: r.role for r in rows}
    assert roles[w.topic_ids["VIII.2"]] is TopicRole.PRIMARY
    assert roles[w.topic_ids["VIII.1"]] is TopicRole.SECONDARY


def test_unsettled_primary_mapping_is_skipped(db):
    w = build_world(db)
    _map_row(db, w, w.chunk_ids["1"], "VIII.2", primary=True, status=MappingStatus.REVIEW_REQUIRED)
    _map_row(db, w, w.chunk_ids["2"], "VIII.1", primary=True, status=MappingStatus.REJECTED)
    _map_row(db, w, w.chunk_ids["3"], "VIII.3", primary=True, status=MappingStatus.APPROVED)

    res = rebuild_exercise_topics(db)
    assert res.skipped_unsettled == 2
    assert res.exercises_with_topics == 1  # only the APPROVED one


def test_touch_count_is_primary_or_secondary_distinct(db):
    w = build_world(db)
    # two exercises: ex1 primary VIII.1, ex2 secondary VIII.1
    _map_row(db, w, w.chunk_ids["1"], "VIII.1", primary=True, status=MappingStatus.AI_SUGGESTED)
    _map_row(db, w, w.chunk_ids["2"], "VIII.2", primary=True, status=MappingStatus.AI_SUGGESTED)
    _map_row(db, w, w.chunk_ids["2"], "VIII.1", primary=False, status=MappingStatus.AI_SUGGESTED, conf=0.4)
    rebuild_exercise_topics(db)

    by_code = {c.code: c for c in topic_chunk_counts(db)}
    assert by_code["VIII.1"].primary == 1   # only ex1
    assert by_code["VIII.1"].touch == 2     # ex1 + ex2
    assert by_code["VIII.2"].primary == 1
    assert by_code["VIII.3"].primary == 0


def test_secondary_equal_to_primary_topic_is_not_double_counted(db):
    w = build_world(db)
    _map_row(db, w, w.chunk_ids["1"], "VIII.1", primary=True, status=MappingStatus.AI_SUGGESTED)
    _map_row(db, w, w.chunk_ids["1"], "VIII.1", primary=False, status=MappingStatus.AI_SUGGESTED, conf=0.3)
    res = rebuild_exercise_topics(db)
    assert res.primary_rows == 1 and res.secondary_rows == 0


def test_rebuild_is_idempotent(db):
    w = build_world(db)
    _map_row(db, w, w.chunk_ids["1"], "VIII.2", primary=True, status=MappingStatus.AI_SUGGESTED)
    a = rebuild_exercise_topics(db)
    b = rebuild_exercise_topics(db)
    assert (a.primary_rows, a.secondary_rows) == (b.primary_rows, b.secondary_rows)
    assert db.query(ExerciseTopic).count() == 1


def test_full_statement_latex_prepends_the_stem(db):
    from zaspro.db.models import (
        Exercise, ExerciseOrigin, VerificationStatus,
    )

    w = build_world(db)
    parent = Exercise(
        source_document_id=w.document_id, exercise_number="9",
        statement="stem plain", statement_latex_raw="stem $x$",
        origin=ExerciseOrigin.OFFICIAL, verbatim_ok=True,
        verification_status=VerificationStatus.DRAFT,
    )
    db.add(parent)
    db.flush()
    child = Exercise(
        source_document_id=w.document_id, exercise_number="9.1",
        parent_exercise_id=parent.id,
        statement="body plain", statement_latex_raw="body $y$",
        origin=ExerciseOrigin.OFFICIAL, verbatim_ok=True, points_available=1,
        verification_status=VerificationStatus.DRAFT,
    )
    db.add(child)
    db.flush()
    assert child.full_statement == "stem plain\n\nbody plain"
    assert child.full_statement_latex == "stem $x$\n\nbody $y$"
    assert parent.full_statement_latex == "stem $x$"
