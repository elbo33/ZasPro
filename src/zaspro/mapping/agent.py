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

# v2: the parent's shared stem is now passed with every subtask fragment. v1
# mappings of subtasks were made on the bare subtask body and are not
# comparable — see ADR 0009 and `flag_stem_defect_reviews`.
PROMPT_VERSION = "m3-map-v2"

# A mapping at or above this confidence is trusted straight away
# (`mapping_status = AI_SUGGESTED`) and never reaches the review queue *unless*
# the audit sampler picks it. Below it, the mapping is `REVIEW_REQUIRED` and a
# `ReviewItem` is created. This is the "deterministically extracted chunks do
# not clutter the queue" lever (SPEC §9).
#
# Validated by two calibration passes on MMAP-P0-660-A-2405-arkusz.docx, 37
# reviewed mappings each: v1 single-topic and v2 multi-topic (migration 0006).
# Both agree — every correction fell below 0.8, everything at/above was accepted
# unchanged. Thin evidence still (one paper, one reviewer, bands below 0.8
# small); the 3% audit sampler keeps feeding the curve. A parameter of
# `map_chunk` / `map_document` / `MAP_CHUNK`, not a baked constant. See ADR 0009.
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
    # the shared problem statement from the parent task, for a subtask fragment.
    # A subtask read without it ("the 50th term of the sequence is …") is
    # usually unmappable. NULL for a top-level task.
    stem: str | None = None
    stem_latex: str | None = None
    current_content_type: ContentType
    candidates: list[TopicRef]


class Usage(BaseModel):
    """Token usage from one agent call. Only the real agent sets it.

    The three input figures are disjoint and additive:
      * `input_tokens`  — fresh input, billed at the base rate
      * `cache_write`   — cache_creation_input_tokens, billed at 1.25x (5-min)
      * `cache_read`    — cache_read_input_tokens, billed at 0.1x
    `output_tokens` includes thinking tokens (billed as output).
    """

    input_tokens: int = 0
    output_tokens: int = 0
    cache_read: int = 0
    cache_write: int = 0


class SecondaryTopic(BaseModel):
    """Another requirement the fragment also genuinely tests, ranked below the
    primary. Not "possible" — a reviewer will see it and may promote it."""

    topic_id: int
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str = Field(min_length=1, max_length=1000)

    @field_validator("rationale")
    @classmethod
    def _trim(cls, v: str) -> str:
        return v.strip()


class MappingResult(BaseModel):
    """The agent's structured answer. `topic_id` is `None` when no candidate
    fits — an unmapped chunk is a legitimate outcome (SPEC §10), not an error.

    `secondary_topics` holds the other requirements the fragment also plausibly
    tests. Most fragments have none; ~1/3 of exam tasks have one or more."""

    topic_id: int | None = Field(
        None, description="topic_id of the primary candidate, or null if none fits"
    )
    content_type: ContentType = Field(description="the chunk's content type")
    difficulty: int | None = Field(None, ge=1, le=5, description="1 easiest .. 5 hardest")
    confidence: float = Field(ge=0.0, le=1.0, description="0..1 confidence in the primary")
    rationale: str = Field(min_length=1, max_length=2000)
    secondary_topics: list[SecondaryTopic] = Field(default_factory=list)

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
        blob = " ".join(
            filter(None, [request.heading, request.stem, request.stem_latex,
                          request.text, request.latex])
        )

        cited = [c for c in _CODE_IN_TEXT.findall(blob) if c in by_code]
        if cited:
            ranked = [c for c, _ in Counter(cited).most_common()]
            top = ranked[0]
            distinct = len(ranked)
            # one clear citation -> high; several competing -> middling
            confidence = 0.92 if distinct == 1 else max(0.45, 0.92 - 0.15 * (distinct - 1))
            secondaries = [
                SecondaryTopic(
                    topic_id=by_code[c].topic_id,
                    confidence=round(max(0.3, confidence - 0.1 * (i + 1)), 2),
                    rationale=f"chunk also cites {c}",
                )
                for i, c in enumerate(ranked[1:])
            ]
            return MappingResult(
                topic_id=by_code[top].topic_id,
                content_type=request.current_content_type,
                difficulty=None,
                confidence=round(confidence, 2),
                rationale=(
                    f"chunk cites requirement code(s) {sorted(set(cited))}; "
                    f"picked {top}"
                ),
                secondary_topics=secondaries,
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
You map one fragment of a Polish Matura mathematics exam paper to the \
curriculum requirements from the podstawa programowa (2024) that it tests.

You are given the fragment and a closed list of candidate requirements, each \
with its official code (e.g. "VIII.4"), its unit numeral, and its text. When \
the fragment is a subtask, its parent's shared problem statement is given \
first as SHARED STEM — read the stem and the fragment together; the stem \
usually carries the objects (a function, a sequence, a figure) the subtask \
refers to.

Pick the ONE requirement the fragment most directly exercises as the PRIMARY \
(topic_id). If no candidate genuinely fits, return topic_id = null rather than \
forcing a match — an unmapped fragment is acceptable, useful signal.

Then list, as secondary_topics, every OTHER candidate the fragment genuinely \
also tests — not everything vaguely related, only requirements a teacher would \
agree are exercised. Many fragments have none. A fragment that, say, builds a \
system of equations from a word problem AND requires interpreting a linear \
coefficient tests two requirements; record both. Each secondary gets its own \
confidence and a one-line reason.

Confidence is about being RIGHT, not about primacy: 0.9+ when the fragment \
plainly tests exactly that requirement; 0.5-0.8 when it is defensible but you \
are choosing among a few; below 0.4 when guessing. If your primary confidence \
is mid-range only because two requirements compete for "primary", that is \
exactly the case where the loser belongs in secondary_topics.

difficulty is 1 (trivial) to 5 (hard Matura problem) for the fragment as a \
task, or null if it is not a task. Keep every rationale to one or two sentences.

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
                "description": "topic_id of the PRIMARY candidate, or null",
            },
            "content_type": {
                "type": "string",
                "enum": [c.value for c in ContentType],
            },
            "difficulty": {"type": ["integer", "null"], "minimum": 1, "maximum": 5},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "rationale": {"type": "string"},
            "secondary_topics": {
                "type": "array",
                "description": "other requirements the fragment genuinely also tests",
                "items": {
                    "type": "object",
                    "properties": {
                        "topic_id": {"type": "integer"},
                        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                        "rationale": {"type": "string"},
                    },
                    "required": ["topic_id", "confidence", "rationale"],
                },
            },
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
        self.last_usage: Usage | None = None

    def _client_lazy(self):
        if self._client is None:
            import anthropic  # imported lazily so the stub path needs no key

            from zaspro.config import get_settings

            # Pass the key from our config explicitly: pydantic-settings reads
            # `.env`, the anthropic SDK on its own only reads os.environ, so a
            # key in `.env` alone would otherwise be invisible here.
            key = get_settings().anthropic_api_key
            self._client = (
                anthropic.Anthropic(api_key=key) if key else anthropic.Anthropic()
            )
        return self._client

    def preflight(self) -> str:
        """One tiny real call, so a bad key / model / network fails before a
        batch is enqueued. Returns the model id the API echoed back."""

        client = self._client_lazy()
        msg = client.messages.create(
            model=self.model,
            max_tokens=1,
            messages=[{"role": "user", "content": "ok"}],
        )
        return getattr(msg, "model", self.model)

    @staticmethod
    def _candidates_block(req: MappingRequest) -> str:
        """Stable across every call in a run (same 73 podstawowy requirements,
        deterministic order) — the prompt-cache prefix."""
        cands = "\n".join(
            f"- topic_id={c.topic_id}  {c.code}  (unit {c.unit})  {c.name}"
            for c in req.candidates
        )
        return f"CANDIDATE REQUIREMENTS ({len(req.candidates)}):\n{cands}\n"

    @staticmethod
    def _fragment_block(req: MappingRequest) -> str:
        stem = ""
        if req.stem or req.stem_latex:
            stem = (
                "SHARED STEM (the parent task's problem statement — this "
                "fragment is a subtask of it):\n"
                f"{req.stem_latex or req.stem}\n\n"
            )
        return (
            f"{stem}"
            f"FRAGMENT heading: {req.heading or '—'}\n"
            f"FRAGMENT content type so far: {req.current_content_type.value}\n"
            f"FRAGMENT text:\n{req.text}\n\n"
            f"FRAGMENT latex:\n{req.latex or '—'}\n"
        )

    def map(self, request: MappingRequest) -> MappingResult:
        client = self._client_lazy()
        _cache = {"type": "ephemeral"}
        msg = client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            thinking={"type": "adaptive"},
            system=[{"type": "text", "text": _SYSTEM, "cache_control": _cache}],
            tools=[{**_TOOL, "cache_control": _cache}],
            messages=[
                {
                    "role": "user",
                    "content": [
                        # cached prefix: system + tools + the candidate list
                        {
                            "type": "text",
                            "text": self._candidates_block(request),
                            "cache_control": _cache,
                        },
                        # varies per chunk — not cached
                        {"type": "text", "text": self._fragment_block(request)},
                    ],
                }
            ],
        )
        u = getattr(msg, "usage", None)
        self.last_usage = Usage(
            input_tokens=getattr(u, "input_tokens", 0) or 0,
            output_tokens=getattr(u, "output_tokens", 0) or 0,
            cache_read=getattr(u, "cache_read_input_tokens", 0) or 0,
            cache_write=getattr(u, "cache_creation_input_tokens", 0) or 0,
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
