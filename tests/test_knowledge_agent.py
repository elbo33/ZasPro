"""ClaudeKnowledgeAgent call shape — must stream (max_tokens=32k exceeds the
SDK's 10-minute non-streaming ceiling), keep 32k, and record usage."""

from __future__ import annotations

import types

from zaspro.knowledge.agent import ClaudeKnowledgeAgent, KnowledgeRequest


class _Stream:
    def __init__(self, msg, calls):
        self._msg = msg
        self._calls = calls

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def get_final_message(self):
        self._calls["get_final_message"] = True
        return self._msg


class _FakeMessages:
    def __init__(self, msg, calls):
        self._msg = msg
        self._calls = calls

    def create(self, **kw):  # must NOT be used
        self._calls["create"] = kw
        raise AssertionError("knowledge agent must stream, not create()")

    def stream(self, **kw):
        self._calls["stream_kwargs"] = kw
        return _Stream(self._msg, self._calls)


def _msg():
    usage = types.SimpleNamespace(
        input_tokens=1234, output_tokens=30000,
        cache_read_input_tokens=1600, cache_creation_input_tokens=0,
    )
    block = types.SimpleNamespace(
        type="tool_use", name="record_knowledge",
        input={"concepts": [{"name": "c", "description": "d",
                             "from_exercises": ["1"], "evidence": "e"}]},
    )
    return types.SimpleNamespace(usage=usage, content=[block])


def test_extract_streams_keeps_32k_and_records_usage():
    calls: dict = {}
    agent = ClaudeKnowledgeAgent()
    agent._client = types.SimpleNamespace(messages=_FakeMessages(_msg(), calls))

    out = agent.extract(KnowledgeRequest(
        topic_code="I.1", topic_name="liczby", requirement_text="…",
        exercises=[],
    ))

    assert "stream_kwargs" in calls and "create" not in calls
    assert calls["stream_kwargs"]["max_tokens"] == 32000
    assert calls["get_final_message"] is True
    assert [c.name for c in out.concepts] == ["c"]
    assert agent.last_usage == {
        "in": 1234, "out": 30000, "cache_read": 1600, "cache_write": 0,
    }
