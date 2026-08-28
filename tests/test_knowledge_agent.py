"""ClaudeKnowledgeAgent call shape: streams, splits into two calls, sums usage,
fails loudly on truncation, and treats the `<parameter>` malformation as a
transient (re-sampled) failure — distinct from a genuine schema violation."""

from __future__ import annotations

import json
import types

import pytest

from zaspro.jobs import PermanentJobError
from zaspro.knowledge import agent as kagent
from zaspro.knowledge.agent import (
    ClaudeKnowledgeAgent, KnowledgeError, KnowledgeMalformed, KnowledgeRequest,
    KnowledgeTruncated,
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
        return self._msg


class _FakeMessages:
    """Per tool name: a single message or a list consumed in order (the last
    entry repeats once the list is exhausted). Records every stream() call."""

    def __init__(self, by_tool, calls):
        self._seqs = {
            k: (list(v) if isinstance(v, list) else [v]) for k, v in by_tool.items()
        }
        self._calls = calls

    def create(self, **kw):
        raise AssertionError("knowledge agent must stream, not create()")

    def stream(self, **kw):
        tool_name = kw["tools"][0]["name"]
        self._calls.setdefault("stream", []).append(
            {"tool": tool_name, "max_tokens": kw["max_tokens"], "thinking": "thinking" in kw}
        )
        seq = self._seqs[tool_name]
        msg = seq.pop(0) if len(seq) > 1 else seq[0]
        return _Stream(msg, self._calls)


def _msg(tool_name, payload, *, stop_reason="tool_use", out_tokens=1000):
    usage = types.SimpleNamespace(
        input_tokens=500, output_tokens=out_tokens,
        cache_read_input_tokens=100, cache_creation_input_tokens=0,
    )
    block = types.SimpleNamespace(type="tool_use", name=tool_name, input=payload)
    return types.SimpleNamespace(usage=usage, content=[block], stop_reason=stop_reason)


_OK_STRUCT = {"concepts": [{"name": "c", "description": "d",
                            "from_exercises": ["1"], "evidence": "e"}],
              "formulas": [], "methods": [], "flags": []}
_OK_PEDA = {"examples": [], "objectives": [], "misconceptions": [], "flags": []}
_PSEUDO = {"concepts": '\n<parameter name="concepts">\n[{"name": "x"}]\n</parameter>'}


def _req():
    return KnowledgeRequest(topic_code="I.1", topic_name="liczby",
                            requirement_text="…", exercises=[])


def _agent(by_tool):
    calls: dict = {}
    a = ClaudeKnowledgeAgent()
    a._client = types.SimpleNamespace(messages=_FakeMessages(by_tool, calls))
    return a, calls


def test_extract_makes_two_calls_merges_and_sums_usage():
    a, calls = _agent({
        "record_structure": _msg("record_structure", _OK_STRUCT, out_tokens=2000),
        "record_pedagogy": _msg("record_pedagogy", {
            **_OK_PEDA,
            "misconceptions": [{
                "name": "m", "incorrect_reasoning": "x", "correct_reasoning": "y",
                "source_kind": "AGENT_INFERENCE", "from_exercises": ["1"], "evidence": "Zad 1",
            }],
        }, out_tokens=3000),
    })
    out = a.extract(_req())

    assert [c["tool"] for c in calls["stream"]] == ["record_structure", "record_pedagogy"]
    assert all(c["max_tokens"] == a.max_tokens for c in calls["stream"])
    assert [c.name for c in out.concepts] == ["c"]
    assert [m.name for m in out.misconceptions] == ["m"]
    assert a.last_usage == {"in": 1000, "out": 5000, "cache_read": 200, "cache_write": 0}
    assert a.malformed_retries == 0


def test_truncation_is_permanent_and_stops_before_the_second_call():
    a, calls = _agent({
        "record_structure": _msg("record_structure", _OK_STRUCT,
                                 stop_reason="max_tokens", out_tokens=32000),
        "record_pedagogy": _msg("record_pedagogy", _OK_PEDA),
    })
    with pytest.raises(KnowledgeTruncated):
        a.extract(_req())
    assert [c["tool"] for c in calls["stream"]] == ["record_structure"]
    assert isinstance(KnowledgeTruncated(), PermanentJobError)


def test_pseudo_syntax_malformation_is_retried_and_recovers():
    a, calls = _agent({
        "record_structure": [_msg("record_structure", _PSEUDO),   # attempt 1: malformed
                             _msg("record_structure", _OK_STRUCT)],  # attempt 2: fine
        "record_pedagogy": _msg("record_pedagogy", _OK_PEDA),
    })
    out = a.extract(_req())

    assert [c["tool"] for c in calls["stream"]] == [
        "record_structure", "record_structure", "record_pedagogy",
    ]
    assert [c.name for c in out.concepts] == ["c"]
    assert a.malformed_retries == 1
    # KnowledgeMalformed is NOT permanent — the worker would retry it
    assert not isinstance(KnowledgeMalformed(), PermanentJobError)
    assert list(kagent.DEBUG_DIR.glob("I.1-record_structure-*.json"))  # still captured


def test_pseudo_syntax_persisting_becomes_permanent_after_the_retries():
    a, calls = _agent({
        "record_structure": _msg("record_structure", _PSEUDO),  # every sample malformed
        "record_pedagogy": _msg("record_pedagogy", _OK_PEDA),
    })
    with pytest.raises(KnowledgeError) as ei:
        a.extract(_req())
    assert isinstance(ei.value, PermanentJobError)
    assert [c["tool"] for c in calls["stream"]] == ["record_structure"] * 3  # 1 + 2 retries
    assert a.malformed_retries == 3


def test_genuine_schema_violation_is_permanent_immediately():
    a, calls = _agent({
        # wrong type, no <parameter> — a real schema violation, not the malformation
        "record_structure": _msg("record_structure", {"concepts": [{"name": 123}]}),
        "record_pedagogy": _msg("record_pedagogy", _OK_PEDA),
    })
    with pytest.raises(KnowledgeError) as ei:
        a.extract(_req())
    assert isinstance(ei.value, PermanentJobError)
    assert [c["tool"] for c in calls["stream"]] == ["record_structure"]  # no retry
    assert a.malformed_retries == 0


def test_no_tool_block_is_permanent_and_dumps_raw():
    text_only = types.SimpleNamespace(
        usage=types.SimpleNamespace(input_tokens=1, output_tokens=1,
                                    cache_read_input_tokens=0, cache_creation_input_tokens=0),
        content=[types.SimpleNamespace(type="text", text="here is the answer ...")],
        stop_reason="end_turn",
    )
    a, _ = _agent({"record_structure": text_only, "record_pedagogy": _msg("record_pedagogy", _OK_PEDA)})
    with pytest.raises(KnowledgeError):
        a.extract(_req())
    assert list(kagent.DEBUG_DIR.glob("I.1-record_structure-*.json"))


def test_transient_api_error_propagates_unwrapped_for_retry():
    class Boom(Exception):
        status_code = 503

    class _M:
        def stream(self, **kw):
            raise Boom("overloaded")

    a = ClaudeKnowledgeAgent()
    a._client = types.SimpleNamespace(messages=_M())
    with pytest.raises(Boom):
        a.extract(_req())


def test_client_4xx_is_wrapped_permanent():
    class Boom(Exception):
        status_code = 400

    class _M:
        def stream(self, **kw):
            raise Boom("context too long")

    a = ClaudeKnowledgeAgent()
    a._client = types.SimpleNamespace(messages=_M())
    with pytest.raises(KnowledgeError):
        a.extract(_req())


def test_thinking_off_omits_the_kwarg():
    a, calls = _agent({
        "record_structure": _msg("record_structure", _OK_STRUCT),
        "record_pedagogy": _msg("record_pedagogy", _OK_PEDA),
    })
    a.thinking = False
    a.extract(_req())
    assert all(c["thinking"] is False for c in calls["stream"])

    b, bcalls = _agent({
        "record_structure": _msg("record_structure", _OK_STRUCT),
        "record_pedagogy": _msg("record_pedagogy", _OK_PEDA),
    })
    b.extract(_req())
    assert all(c["thinking"] is True for c in bcalls["stream"])
