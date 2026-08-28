"""ClaudeKnowledgeAgent call shape: streams, splits into two calls
(structure / pedagogy), fails loudly on truncation, sums usage across calls."""

from __future__ import annotations

import types

import pytest

from zaspro.jobs import PermanentJobError
from zaspro.knowledge import agent as kagent
from zaspro.knowledge.agent import (
    ClaudeKnowledgeAgent, KnowledgeError, KnowledgeRequest, KnowledgeTruncated,
)


@pytest.fixture(autouse=True)
def _debug_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(kagent, "DEBUG_DIR", tmp_path / "knowledge_debug")


class _Stream:
    def __init__(self, msg, calls):
        self._msg, self._calls = msg, calls

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def get_final_message(self):
        self._calls.setdefault("get_final_message", 0)
        self._calls["get_final_message"] += 1
        return self._msg


class _FakeMessages:
    """Returns a canned message per tool name; records every stream() call."""

    def __init__(self, by_tool, calls):
        self._by_tool, self._calls = by_tool, calls

    def create(self, **kw):
        raise AssertionError("knowledge agent must stream, not create()")

    def stream(self, **kw):
        tool_name = kw["tools"][0]["name"]
        self._calls.setdefault("stream", []).append(
            {"tool": tool_name, "max_tokens": kw["max_tokens"]}
        )
        return _Stream(self._by_tool[tool_name], self._calls)


def _msg(tool_name, payload, *, stop_reason="tool_use", out_tokens=1000):
    usage = types.SimpleNamespace(
        input_tokens=500, output_tokens=out_tokens,
        cache_read_input_tokens=100, cache_creation_input_tokens=0,
    )
    block = types.SimpleNamespace(type="tool_use", name=tool_name, input=payload)
    return types.SimpleNamespace(usage=usage, content=[block], stop_reason=stop_reason)


def _req():
    return KnowledgeRequest(topic_code="I.1", topic_name="liczby",
                            requirement_text="…", exercises=[])


def test_extract_makes_two_calls_merges_and_sums_usage():
    calls: dict = {}
    agent = ClaudeKnowledgeAgent()
    agent._client = types.SimpleNamespace(messages=_FakeMessages({
        "record_structure": _msg("record_structure", {
            "concepts": [{"name": "c", "description": "d",
                          "from_exercises": ["1"], "evidence": "e"}],
            "formulas": [], "methods": [], "flags": [],
        }, out_tokens=2000),
        "record_pedagogy": _msg("record_pedagogy", {
            "examples": [], "objectives": [],
            "misconceptions": [{
                "name": "m", "incorrect_reasoning": "x", "correct_reasoning": "y",
                "source_kind": "AGENT_INFERENCE", "from_exercises": ["1"],
                "evidence": "Zad 1",
            }],
            "flags": [],
        }, out_tokens=3000),
    }, calls))

    out = agent.extract(_req())

    assert [c["tool"] for c in calls["stream"]] == ["record_structure", "record_pedagogy"]
    assert all(c["max_tokens"] == agent.max_tokens for c in calls["stream"])
    assert [c.name for c in out.concepts] == ["c"]
    assert [m.name for m in out.misconceptions] == ["m"]
    assert agent.last_usage == {  # summed across both calls
        "in": 1000, "out": 5000, "cache_read": 200, "cache_write": 0,
    }


def test_truncation_raises_and_does_not_return_a_partial():
    calls: dict = {}
    agent = ClaudeKnowledgeAgent()
    agent._client = types.SimpleNamespace(messages=_FakeMessages({
        "record_structure": _msg(
            "record_structure",
            {"concepts": [{"name": "c", "description": "d",
                           "from_exercises": [], "evidence": "e"}]},
            stop_reason="max_tokens", out_tokens=32000,
        ),
        "record_pedagogy": _msg("record_pedagogy", {}),
    }, calls))

    with pytest.raises(KnowledgeTruncated):
        agent.extract(_req())
    # never reached the second call
    assert [c["tool"] for c in calls["stream"]] == ["record_structure"]
    assert isinstance(KnowledgeTruncated(), PermanentJobError)


def test_schema_invalid_tool_input_is_permanent_and_dumps_raw():
    """The real failure: tool_use.input is a dict whose `concepts` value is a
    string of XML-style <parameter name=...> tags, not a list."""
    calls: dict = {}
    bad = {"concepts": '\n<parameter name="concepts">\n[{"name": "x"}]\n</parameter>'}
    agent = ClaudeKnowledgeAgent()
    agent._client = types.SimpleNamespace(messages=_FakeMessages({
        "record_structure": _msg("record_structure", bad),
        "record_pedagogy": _msg("record_pedagogy", {}),
    }, calls))

    with pytest.raises(KnowledgeError) as ei:
        agent.extract(_req())
    assert isinstance(ei.value, PermanentJobError)         # worker won't retry
    assert [c["tool"] for c in calls["stream"]] == ["record_structure"]
    dumps = list((kagent.DEBUG_DIR).glob("I.1-record_structure-*.json"))
    assert len(dumps) == 1
    import json
    raw = json.loads(dumps[0].read_text())
    assert raw["content"][0]["input"] == bad              # verbatim, unabridged
    assert raw["content"][0]["input_python_type"] == "dict"


def test_no_tool_block_is_permanent_and_dumps_raw():
    calls: dict = {}
    text_only = types.SimpleNamespace(
        usage=types.SimpleNamespace(input_tokens=1, output_tokens=1,
                                    cache_read_input_tokens=0, cache_creation_input_tokens=0),
        content=[types.SimpleNamespace(type="text", text="here is the answer ...")],
        stop_reason="end_turn",
    )
    agent = ClaudeKnowledgeAgent()
    agent._client = types.SimpleNamespace(messages=_FakeMessages(
        {"record_structure": text_only, "record_pedagogy": _msg("record_pedagogy", {})}, calls))

    with pytest.raises(KnowledgeError):
        agent.extract(_req())
    assert list((kagent.DEBUG_DIR).glob("I.1-record_structure-*.json"))


def test_transient_api_error_propagates_unwrapped_for_retry():
    class Boom(Exception):
        status_code = 503  # service unavailable — transient

    class _M:
        def stream(self, **kw):
            raise Boom("overloaded")

    agent = ClaudeKnowledgeAgent()
    agent._client = types.SimpleNamespace(messages=_M())
    with pytest.raises(Boom):                              # NOT KnowledgeError
        agent.extract(_req())


def test_client_4xx_is_wrapped_permanent():
    class Boom(Exception):
        status_code = 400  # bad request — deterministic

    class _M:
        def stream(self, **kw):
            raise Boom("context too long")

    agent = ClaudeKnowledgeAgent()
    agent._client = types.SimpleNamespace(messages=_M())
    with pytest.raises(KnowledgeError):
        agent.extract(_req())
