"""Section Knowledge Agent: stub shape + ClaudeSectionAgent call shape."""

from __future__ import annotations

import types

import pytest

from zaspro.knowledge.agent import (
    ClaudeSectionAgent, KnowledgeError, RequirementCtx, SectionRequest,
    StubSectionAgent,
)


def _req():
    return SectionRequest(
        slug="funkcja-liniowa", name="Funkcja liniowa",
        scope="the linear function y = ax + b",
        requirements=[RequirementCtx(code="V.5", text="interpretuje współczynniki")],
    )


def test_stub_writes_a_full_spec_with_no_exercises_needed():
    out = StubSectionAgent().write(_req())
    assert out.concepts and out.formulas and out.methods
    assert len(out.examples) >= 2
    assert out.misconceptions and out.objectives


class _Stream:
    def __init__(self, msg):
        self._msg = msg

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def get_final_message(self):
        return self._msg


def _msg(payload, *, stop_reason="tool_use"):
    usage = types.SimpleNamespace(
        input_tokens=900, output_tokens=18000,
        cache_read_input_tokens=0, cache_creation_input_tokens=0,
    )
    block = types.SimpleNamespace(type="tool_use", name="record_section", input=payload)
    return types.SimpleNamespace(usage=usage, content=[block], stop_reason=stop_reason)


def _agent(msg):
    calls: dict = {}

    class _M:
        def create(self, **kw):
            raise AssertionError("must stream")

        def stream(self, **kw):
            calls["kw"] = kw
            return _Stream(msg)

    a = ClaudeSectionAgent()
    a._client = types.SimpleNamespace(messages=_M())
    return a, calls


_OK = {
    "concepts": [{"name": "slope", "definition": "rise over run"}],
    "formulas": [{"name": "line", "latex": "y = ax + b"}],
    "methods": [], "examples": [], "misconceptions": [], "objectives": [],
}


def test_write_streams_one_call_and_records_usage():
    a, calls = _agent(_msg(_OK))
    out = a.write(_req())
    assert calls["kw"]["max_tokens"] == a.max_tokens
    assert calls["kw"]["tools"][0]["name"] == "record_section"
    assert [c.name for c in out.concepts] == ["slope"]
    assert a.last_usage == {"in": 900, "out": 18000, "cache_read": 0, "cache_write": 0}


def test_no_tool_call_raises_knowledge_error():
    text_only = types.SimpleNamespace(
        usage=types.SimpleNamespace(input_tokens=1, output_tokens=1,
                                    cache_read_input_tokens=0, cache_creation_input_tokens=0),
        content=[types.SimpleNamespace(type="text", text="...")],
        stop_reason="end_turn",
    )
    a, _ = _agent(text_only)
    with pytest.raises(KnowledgeError):
        a.write(_req())


def test_schema_mismatch_raises_knowledge_error():
    a, _ = _agent(_msg({"concepts": [{"name": 123}]}))  # missing 'definition', wrong type
    with pytest.raises(KnowledgeError):
        a.write(_req())


def test_api_exception_is_wrapped():
    class _M:
        def stream(self, **kw):
            raise RuntimeError("boom")

    a = ClaudeSectionAgent()
    a._client = types.SimpleNamespace(messages=_M())
    with pytest.raises(KnowledgeError):
        a.write(_req())
