"""FastAPI review endpoints (SPEC §16, §17). Simulates the keyboard-only
review loop: GET /review/next, POST /review/{id}/decision, repeat."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from tests.fixtures.mapping_world import build_world
from zaspro.api.app import create_app
from zaspro.api.deps import get_db
from zaspro.mapping import StubMappingAgent, map_document


@pytest.fixture
def client(db):
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db
    return TestClient(app)


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_deterministic_confident_mappings_do_not_reach_the_queue(client, db):
    w = build_world(db)
    map_document(db, w.document_id, StubMappingAgent(), inline=True)

    stats = client.get("/review/queue").json()
    # chunks 1 and 4 map confidently to VIII.2 and must be absent from the queue
    assert stats["mappings_by_status"]["AI_SUGGESTED"] >= 2
    assert stats["open_total"] == stats["by_type"]["CURRICULUM_MAPPING"]
    assert stats["open_total"] <= 2  # only the uncertain ones
    assert stats["unmapped_chunks"] == 0


def test_keyboard_review_loop_approve_and_reject(client, db):
    w = build_world(db)
    map_document(db, w.document_id, StubMappingAgent(), inline=True)

    # 'a' -> approve the first item
    item = client.get("/review/next").json()
    assert item is not None
    assert item["mapping"] is not None
    assert item["candidates"], "edit needs the candidate list inline"
    r = client.post(
        f"/review/{item['id']}/decision",
        json={"reviewer": "elie", "decision": "APPROVE"},
    ).json()
    assert r["ok"] is True
    approved_id = item["id"]

    # server hands back the next item with no extra round-trip
    nxt = r["next"]
    if nxt is not None:
        assert nxt["id"] != approved_id
        # 'r' -> reject with a reason code
        rr = client.post(
            f"/review/{nxt['id']}/decision",
            json={
                "reviewer": "elie",
                "decision": "REJECT",
                "reason_code": "NOT_CURRICULUM",
            },
        )
        assert rr.status_code == 200

    # queue drains
    final = client.get("/review/queue").json()
    assert final["open_total"] == 0
    assert client.get("/review/next").status_code == 204


def test_reject_without_reason_is_409(client, db):
    w = build_world(db)
    map_document(db, w.document_id, StubMappingAgent(), inline=True)
    item = client.get("/review/next").json()
    r = client.post(
        f"/review/{item['id']}/decision",
        json={"reviewer": "elie", "decision": "REJECT"},
    )
    assert r.status_code == 409
    assert "reason_code" in r.json()["detail"]


def test_curriculum_and_sources_pages(client, db):
    w = build_world(db)
    map_document(db, w.document_id, StubMappingAgent(), inline=True)

    tree = client.get("/curriculum").json()
    assert tree and tree[0]["code"] == "VIII"
    codes = {t["code"] for u in tree for t in u["topics"]}
    assert codes == {"VIII.1", "VIII.2", "VIII.3"}  # podstawowy only
    viii2 = next(t for u in tree for t in u["topics"] if t["code"] == "VIII.2")
    assert viii2["mapped_chunks"] >= 2

    srcs = client.get("/sources").json()
    assert len(srcs) == 1
    assert srcs[0]["chunks"] == 4
    doc_id = srcs[0]["id"]
    chunks = client.get(f"/sources/{doc_id}/chunks").json()
    assert len(chunks) == 4
    assert all(c["confidence"] is None for c in chunks)  # deterministic extraction
    assert any(c["mapping"] and c["mapping"]["mapping_status"] == "AI_SUGGESTED" for c in chunks)
