"""Mapping agent + MAP_CHUNK handler (SPEC §10, §12).

The gate half exercised here: a deterministically extracted chunk that maps
*confidently* does NOT create a review item; only an uncertain mapping does.
"""

from __future__ import annotations

import pytest

from tests.fixtures.mapping_world import build_world
from zaspro.db.models import (
    ChunkMapping,
    ContentType,
    Exercise,
    MappingStatus,
    ReviewItem,
    ReviewItemType,
    ReviewStatus,
)
from zaspro.mapping import MappingError, MappingRequest, StubMappingAgent, TopicRef
from zaspro.mapping.agent import MappingResult
from zaspro.mapping.handler import candidate_topics, map_chunk, map_document


def test_candidate_topics_are_podstawowy_only(db):
    build_world(db)
    codes = {c.code for c in candidate_topics(db)}
    assert codes == {"VIII.1", "VIII.2", "VIII.3"}  # VIII.R1 excluded (ADR 0008)


def test_confident_deterministic_mapping_skips_the_queue(db):
    w = build_world(db)
    agent = StubMappingAgent()

    # audit_sample_rate=0 isolates the threshold mechanism from the sampler
    m = map_chunk(db, w.chunk_ids["1"], agent, audit_sample_rate=0.0)

    assert m.topic_id == w.topic_ids["VIII.2"]
    assert m.confidence >= 0.8
    assert m.mapping_status is MappingStatus.AI_SUGGESTED
    assert m.model is None and m.prompt_version == "m3-map-v1"
    # nothing in the queue
    assert db.query(ReviewItem).count() == 0
    # topic mirrored onto the exercise
    ex = db.query(Exercise).filter_by(source_document_id=w.document_id, exercise_number="1").one()
    assert ex.topic_id == w.topic_ids["VIII.2"]


def test_audit_sampler_queues_a_confident_mapping_without_blocking_it(db):
    w = build_world(db)
    # rate 1.0 -> every confident mapping also gets an audit ReviewItem
    m = map_chunk(db, w.chunk_ids["1"], StubMappingAgent(), audit_sample_rate=1.0)

    assert m.mapping_status is MappingStatus.AI_SUGGESTED  # not blocked
    item = db.query(ReviewItem).one()
    assert item.audit_sample is True
    assert item.status.value == "OPEN"
    assert item.risk <= 0.2
    # the confident mapping is still applied to the exercise
    ex = db.query(Exercise).filter_by(
        source_document_id=w.document_id, exercise_number="1"
    ).one()
    assert ex.topic_id == w.topic_ids["VIII.2"]


def test_audit_sampler_is_deterministic_per_chunk(db):
    w = build_world(db)
    # a mid rate: same chunk, same prompt version -> same pick every time
    picks = set()
    for _ in range(3):
        db.query(ReviewItem).delete()
        db.query(ChunkMapping).delete()
        db.flush()
        map_chunk(db, w.chunk_ids["1"], StubMappingAgent(), audit_sample_rate=0.5)
        picks.add(db.query(ReviewItem).count())
    assert len(picks) == 1  # stable


def test_unmappable_chunk_enters_the_queue_as_review_required(db):
    w = build_world(db)
    m = map_chunk(db, w.chunk_ids["3"], StubMappingAgent())

    assert m.topic_id is None
    assert m.mapping_status is MappingStatus.REVIEW_REQUIRED
    item = db.query(ReviewItem).one()
    assert item.item_type is ReviewItemType.CURRICULUM_MAPPING
    assert item.ref_table == "chunk_mappings" and item.ref_id == m.id
    assert item.status is ReviewStatus.OPEN
    assert item.risk == pytest.approx(1.0 - m.confidence, abs=1e-4)
    assert item.source_document_id == w.document_id
    # an unreviewed guess is NOT carried onto the exercise
    ex = db.query(Exercise).filter_by(source_document_id=w.document_id, exercise_number="3").one()
    assert ex.topic_id is None


def test_map_chunk_is_idempotent(db):
    w = build_world(db)
    a = map_chunk(db, w.chunk_ids["1"], StubMappingAgent())
    b = map_chunk(db, w.chunk_ids["1"], StubMappingAgent())
    assert a.id == b.id
    assert db.query(ChunkMapping).count() == 1


def test_business_rule_rejects_a_topic_outside_the_candidate_set(db):
    w = build_world(db)

    class RogueAgent:
        name, model, prompt_version = "rogue", None, "x"

        def map(self, request: MappingRequest) -> MappingResult:
            return MappingResult(
                topic_id=w.topic_ids["VIII.R1"],  # rozszerzony — not offered
                content_type=ContentType.EXERCISE,
                confidence=0.99,
                rationale="picked a deferred rozszerzony topic",
            )

    with pytest.raises(MappingError, match="not a podstawowy requirement"):
        map_chunk(db, w.chunk_ids["1"], RogueAgent())
    assert db.query(ChunkMapping).count() == 0


def test_map_document_inline_counts(db):
    w = build_world(db)
    summary = map_document(db, w.document_id, StubMappingAgent(), inline=True)
    assert summary["chunks"] == 4
    assert summary["auto"] + summary["review"] == 4
    assert summary["auto"] >= 2  # chunks 1 and 4 cite VIII.2
    assert summary["unmapped"] >= 1  # chunk 3


def test_map_document_enqueues_jobs_by_default(db):
    from zaspro.db.models import Job, JobType

    w = build_world(db)
    summary = map_document(db, w.document_id, StubMappingAgent())
    assert summary["jobs"] == 4
    assert db.query(Job).filter_by(job_type=JobType.MAP_CHUNK).count() == 4


def test_stub_needs_no_api_key():
    # the offline path must not construct an Anthropic client
    agent = StubMappingAgent()
    r = agent.map(
        MappingRequest(
            source_chunk_id=1,
            heading="Zadanie 5.",
            text="nic konkretnego",
            latex=None,
            current_content_type=ContentType.EXERCISE,
            candidates=[TopicRef(topic_id=1, code="I.1", unit="I", name="liczby", level="podstawowy")],
        )
    )
    assert 0.0 <= r.confidence <= 1.0
