"""The Mapping Agent (SPEC §12, agent 2): a source chunk -> a curriculum
location, with a *mapping* confidence that is separate from extraction
confidence (SPEC §10).

Contract, like every agent (SPEC §12):

    LLM -> structured response -> Pydantic validation -> business-rule
    validation -> database

Never LLM -> database. `agent.py` owns only the first two arrows: it returns a
validated `MappingResult`. Business rules and persistence live in `handler.py`.

Two implementations:

* `StubMappingAgent` — offline, deterministic. Reads the requirement codes the
  chunk already cites (arkusz `zasady` boxes cite `I.4)` etc.) and falls back to
  token overlap. Used in tests and whenever `ANTHROPIC_API_KEY` is unset, so the
  whole M3 path runs without the network.
* `ClaudeMappingAgent` — the real call (`claude-opus-5`, adaptive thinking, a
  single structured tool). Exercised only when a key is present.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from typing import Protocol

from pydantic import BaseModel, Field, field_validator

from zaspro.db.models import ContentType

PROMPT_VERSION = "m3-map-v1"

# A mapping at or above this confidence is trusted straight away
# (`mapping_status = AI_SUGGESTED`) and never reaches the review queue *unless*
# the audit sampler picks it. Below it, the mapping is `REVIEW_REQUIRED` and a
# `ReviewItem` is created. This single number is the "deterministically
# extracted chunks do not clutter the queue" lever (SPEC §9): clean pandoc text
# maps confidently, so it sails through. Provisional until a calibration pass
# (`zaspro.mapping.run --review-all`) fixes it from evidence — see ADR 0009.
AUTO_APPROVE_THRESHOLD = 0.80

# A permanent random fraction of *confident* mappings is queued anyway, flagged
# `audit_sample`, so no threshold setting can ever put the system in a state
# where a large block is auto-approved with no human ever seeing a sample. Not
# reachable-to-zero without a code change; tune after calibration.
DEFAULT_AUDIT_SAMPLE_RATE = 0.03


class TopicRef(BaseModel):
    """One candidate curriculum location shown to the agent."""

    topic_id: int
    code: str  # official_requirement_code, e.g. "VIII.4"
    unit: str  # Roman unit numeral
    name: str
    level: str


class MappingRequest(BaseModel):
    source_chunk_id: int
    heading: str | None
    text: str
    latex: str | None
    current_content_type: ContentType
    candidates: list[TopicRef]


class MappingResult(BaseModel):
    """The agent's structured answer. `topic_id` is `None` when no candidate
    fits — an unmapped chunk is a legitimate outcome (SPEC §10), not an error."""

    topic_id: int | None = Field(
        None, description="topic_id of the chosen candidate, or null if none fits"
    )
    content_type: ContentType = Field(description="the chunk's content type")
    difficulty: int | None = Field(None, ge=1, le=5, description="1 easiest .. 5 hardest")
    confidence: float = Field(ge=0.0, le=1.0, description="0..1 mapping confidence")
    rationale: str = Field(min_length=1, max_length=2000)

    @field_validator("rationale")
    @classmethod
    def _trim(cls, v: str) -> str:
        return v.strip()


class MappingError(RuntimeError):
    """The model produced nothing usable; the job should retry."""


class MappingAgent(Protocol):
    name: str
    model: str | None
    prompt_version: str

    def map(self, request: MappingRequest) -> MappingResult: ...


# --------------------------------------------------------------------------- #
# Stub

_CODE_IN_TEXT = re.compile(
    r"\b((?:XIII|XII|XI|X|IX|VIII|VII|VI|IV|V|III|II|I)\.\d+)\)"
)
_WORD = re.compile(r"\w{4,}", re.UNICODE)
_STOP = {
    "oraz", "które", "która", "który", "dla", "jest", "są", "the", "and",
    "zdający", "wyznacz", "oblicz", "podaj", "zadanie", "punkt", "punkty",
}


def _tokens(s: str) -> set[str]:
    return {m.group(0).lower() for m in _WORD.finditer(s)} - _STOP


class StubMappingAgent:
    """Deterministic, offline. Not a model — a cheap signal so the pipeline is
    testable end to end without the network."""

    name = "stub"
    model = None
    prompt_version = PROMPT_VERSION

    def map(self, request: MappingRequest) -> MappingResult:
        by_code = {c.code: c for c in request.candidates}
        blob = " ".join(filter(None, [request.heading, request.text, request.latex]))

        cited = [c for c in _CODE_IN_TEXT.findall(blob) if c in by_code]
        if cited:
            top, n = Counter(cited).most_common(1)[0]
            # one clear citation -> high; several competing -> middling
            distinct = len(set(cited))
            confidence = 0.92 if distinct == 1 else max(0.45, 0.92 - 0.15 * (distinct - 1))
            return MappingResult(
                topic_id=by_code[top].topic_id,
                content_type=request.current_content_type,
                difficulty=None,
                confidence=round(confidence, 2),
                rationale=(
                    f"chunk cites requirement code(s) {sorted(set(cited))}; "
                    f"picked {top}"
                ),
            )

        # fall back to token overlap with candidate requirement prose
        q = _tokens(blob)
        best: TopicRef | None = None
        best_overlap = 0
        for c in request.candidates:
            o = len(q & _tokens(c.name))
            if o > best_overlap:
                best, best_overlap = c, o
        if best is not None and best_overlap >= 2:
            confidence = min(0.6, 0.2 + 0.1 * best_overlap)
            return MappingResult(
                topic_id=best.topic_id,
                content_type=request.current_content_type,
                difficulty=None,
                confidence=round(confidence, 2),
                rationale=f"token overlap ({best_overlap} words) with {best.code}",
            )

        return MappingResult(
            topic_id=None,
            content_type=request.current_content_type,
            difficulty=None,
            confidence=0.1,
            rationale="no cited code and no meaningful token overlap with any candidate",
        )


# --------------------------------------------------------------------------- #
# Claude

_SYSTEM = """\
You map one fragment of a Polish Matura mathematics exam paper to a single \
curriculum requirement from the podstawa programowa (2024).

You are given the fragment and a closed list of candidate requirements, each \
with its official code (e.g. "VIII.4"), its unit numeral, and its text. Choose \
the ONE candidate whose requirement the fragment most directly exercises. If no \
candidate genuinely fits, return topic_id = null rather than forcing a match — \
an unmapped fragment is acceptable and useful signal.

Report calibrated confidence: 0.9+ only when the fragment plainly tests exactly \
that requirement; 0.5-0.8 when it is the best of several plausible; below 0.4 \
when you are guessing. difficulty is 1 (trivial) to 5 (hard Matura problem) for \
the fragment as a task, or null if it is not a task. Keep the rationale to one \
or two sentences.

Call the record_mapping tool exactly once.
"""

_TOOL = {
    "name": "record_mapping",
    "description": "Record the curriculum mapping for the fragment.",
    "input_schema": {
        "type": "object",
        "properties": {
            "topic_id": {
                "type": ["integer", "null"],
                "description": "topic_id of the chosen candidate, or null",
            },
            "content_type": {
                "type": "string",
                "enum": [c.value for c in ContentType],
            },
            "difficulty": {"type": ["integer", "null"], "minimum": 1, "maximum": 5},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "rationale": {"type": "string"},
        },
        "required": ["topic_id", "content_type", "confidence", "rationale"],
    },
}


class ClaudeMappingAgent:
    """The real Mapping Agent. Kept deliberately thin: one message, one forced-
    by-instruction tool call, Pydantic on the way out."""

    name = "claude"
    prompt_version = PROMPT_VERSION

    def __init__(self, *, model: str = "claude-opus-5", max_tokens: int = 16000) -> None:
        self.model = model
        self.max_tokens = max_tokens
        self._client = None

    def _client_lazy(self):
        if self._client is None:
            import anthropic  # imported lazily so the stub path needs no key

            self._client = anthropic.Anthropic()
        return self._client

    def _user_block(self, req: MappingRequest) -> str:
        cands = "\n".join(
            f"- topic_id={c.topic_id}  {c.code}  (unit {c.unit})  {c.name}"
            for c in req.candidates
        )
        return (
            f"FRAGMENT heading: {req.heading or '—'}\n"
            f"FRAGMENT content type so far: {req.current_content_type.value}\n"
            f"FRAGMENT text:\n{req.text}\n\n"
            f"FRAGMENT latex:\n{req.latex or '—'}\n\n"
            f"CANDIDATES ({len(req.candidates)}):\n{cands}\n"
        )

    def map(self, request: MappingRequest) -> MappingResult:
        client = self._client_lazy()
        msg = client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            thinking={"type": "adaptive"},
            system=_SYSTEM,
            tools=[_TOOL],
            messages=[{"role": "user", "content": self._user_block(request)}],
        )
        for block in msg.content:
            if getattr(block, "type", None) == "tool_use" and block.name == "record_mapping":
                data = block.input
                if isinstance(data, str):
                    data = json.loads(data)
                return MappingResult.model_validate(data)
        raise MappingError("model did not call record_mapping")


def default_agent() -> MappingAgent:
    """`ClaudeMappingAgent` when a key is configured, otherwise the stub."""

    from zaspro.config import get_settings

    if get_settings().anthropic_api_key:
        return ClaudeMappingAgent()
    return StubMappingAgent()
