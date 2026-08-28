"""The Knowledge Agent (SPEC §12 agent 3, §11).

Contract: LLM -> structured response -> Pydantic -> business-rule validation ->
database. Hard rules from SPEC §11, enforced in the prompt AND re-checked in
`zaspro.knowledge.extract`:

* concepts / formulas / methods / examples / objectives may not invent facts
  absent from the provided material; each cites the exercise(s) it came from
* sources that disagree -> both readings + a CONFLICT flag, no winner picked
* missing information -> a GAP record, not a filled gap
* misconceptions are the exception (ADR 0011): exam papers do not state student
  errors, so they are *not* suppressed for lack of a citation — they are
  emitted, labelled by `source_kind`, and the low-provenance ones
  (AGENT_INFERENCE / UNSOURCED) are flagged for human approval, which is the
  verification step.

`StubKnowledgeAgent` runs the whole path offline; `ClaudeKnowledgeAgent`
(`claude-opus-5`) is used only from a command the user runs.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

from pydantic import BaseModel, Field, ValidationError

from zaspro.db.models import MisconceptionSource
from zaspro.jobs import PermanentJobError

log = logging.getLogger("zaspro.knowledge.agent")

# raw model responses for failed parses land here, one JSON file per failure
DEBUG_DIR = Path("m4/knowledge_debug")

PROMPT_VERSION = "m4-know-v4"  # v4: two-call split (structure / pedagogy) + hard truncation check; v3 instructions unchanged


class ExerciseCtx(BaseModel):
    number: str
    text: str                       # Exercise.full_statement (stem + body)
    latex: str | None = None        # Exercise.full_statement_latex
    difficulty: int | None = None
    points: int | None = None
    marking_scheme: str | None = None  # the "Zasady oceniania" block for this task


class KnowledgeRequest(BaseModel):
    topic_code: str
    topic_name: str
    requirement_text: str | None = None  # topics.statement_latex / description
    exercises: list[ExerciseCtx]


class _Item(BaseModel):
    from_exercises: list[str] = Field(
        default_factory=list,
        description=(
            "Bare Zadanie numbers this item is drawn from, e.g. [\"11.1\", \"14\"]. "
            "Not \"Zadanie 11.1\", not a sentence — just the numbers. "
            "[] only when the item is from no exercise at all."
        ),
    )
    evidence: str = Field(
        min_length=1, max_length=800,
        description="A short quote or paraphrase from that material naming the task it is from.",
    )


class ConceptOut(_Item):
    name: str
    description: str
    difficulty: int | None = Field(None, ge=1, le=5)


class FormulaOut(_Item):
    name: str
    latex_raw: str
    conditions: str | None = None


class MethodOut(_Item):
    name: str
    when_to_use: str
    steps: list[str] = Field(default_factory=list)


class ExampleOut(_Item):
    statement: str
    worked_solution: str
    difficulty: int | None = Field(None, ge=1, le=5)


class MisconceptionOut(_Item):
    name: str
    incorrect_reasoning: str
    correct_reasoning: str
    severity: int | None = Field(None, ge=1, le=5)
    source_kind: MisconceptionSource
    distractor: str | None = Field(
        None,
        description=(
            "Required when source_kind is DISTRACTOR_INFERENCE: the specific "
            "wrong multiple-choice option(s) the error is read off, e.g. "
            "\"B and D\" or \"C: 20000 · 1,06\". Leave null otherwise."
        ),
    )


class ObjectiveOut(_Item):
    statement: str
    bloom_level: str | None = None


class FlagOut(BaseModel):
    kind: str  # CONFLICT | GAP
    item_kind: str
    detail: str = Field(min_length=1, max_length=800)
    from_exercises: list[str] = Field(default_factory=list)


class KnowledgeExtraction(BaseModel):
    concepts: list[ConceptOut] = Field(default_factory=list)
    formulas: list[FormulaOut] = Field(default_factory=list)
    methods: list[MethodOut] = Field(default_factory=list)
    examples: list[ExampleOut] = Field(default_factory=list)
    misconceptions: list[MisconceptionOut] = Field(default_factory=list)
    objectives: list[ObjectiveOut] = Field(default_factory=list)
    flags: list[FlagOut] = Field(default_factory=list)


# The real agent extracts in two calls so no single response has to carry a
# large topic's whole spec (a 23-exercise topic truncated at 32k output under a
# single call, and reported success with a partial result). Each half is a
# subset of KnowledgeExtraction; `ClaudeKnowledgeAgent.extract` merges them.
class _StructureExtraction(BaseModel):
    concepts: list[ConceptOut] = Field(default_factory=list)
    formulas: list[FormulaOut] = Field(default_factory=list)
    methods: list[MethodOut] = Field(default_factory=list)
    flags: list[FlagOut] = Field(default_factory=list)


class _PedagogyExtraction(BaseModel):
    examples: list[ExampleOut] = Field(default_factory=list)
    objectives: list[ObjectiveOut] = Field(default_factory=list)
    misconceptions: list[MisconceptionOut] = Field(default_factory=list)
    flags: list[FlagOut] = Field(default_factory=list)


class KnowledgeError(PermanentJobError):
    """A deterministic extraction failure — a schema-invalid or truncated model
    response, a missing tool call, a 4xx from the API. Retrying it just fails
    again and costs another call, so the worker fails the job immediately
    (transient errors — connection, 429, 5xx — propagate unwrapped and retry)."""


class KnowledgeTruncated(KnowledgeError):
    """The model hit max_tokens before finishing. The partial tool call is
    discarded and the job fails — never persisted as a complete spec."""


class KnowledgeMalformed(RuntimeError):
    """The model emitted its tool call as Claude's internal `<parameter name=…>`
    pseudo-syntax stuffed into a string argument, instead of a real structured
    tool call. Pydantic is right to reject it. It is intermittent and
    sampling-dependent, so `_call` re-samples; only if it persists across
    `MALFORMED_RETRIES` does it become a `KnowledgeError`. NOT a
    `PermanentJobError` — we never unpack the pseudo-syntax."""


def _is_pseudo_syntax(err: ValidationError) -> bool:
    """True when a rejected value is a string carrying `<parameter name=` — the
    specific malformation, not a generic schema violation."""
    for d in err.errors():
        iv = d.get("input")
        if isinstance(iv, str) and "<parameter name=" in iv:
            return True
    return False


def _usage_dict(u) -> dict:
    return {
        "in": getattr(u, "input_tokens", 0) or 0,
        "out": getattr(u, "output_tokens", 0) or 0,
        "cache_read": getattr(u, "cache_read_input_tokens", 0) or 0,
        "cache_write": getattr(u, "cache_creation_input_tokens", 0) or 0,
    }


def _dump_raw(topic_code: str, tool_name: str, msg) -> str:
    """Write the model's raw content blocks to a file so a parse failure can be
    diagnosed from what the API actually returned, not a truncated traceback."""
    DEBUG_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = DEBUG_DIR / f"{topic_code}-{tool_name}-{ts}.json"
    blocks = []
    for b in getattr(msg, "content", []) or []:
        bt = getattr(b, "type", None)
        d: dict = {"type": bt}
        if bt == "tool_use":
            d["name"] = getattr(b, "name", None)
            d["id"] = getattr(b, "id", None)
            inp = getattr(b, "input", None)
            d["input_python_type"] = type(inp).__name__
            d["input"] = inp  # dict / list / str, verbatim — the whole point
        elif bt == "text":
            d["text"] = getattr(b, "text", None)
        elif bt == "thinking":
            th = getattr(b, "thinking", None) or ""
            d["thinking_len"] = len(th)
            d["thinking_head"] = th[:500]
        else:
            d["repr"] = repr(b)[:2000]
        blocks.append(d)
    payload = {
        "topic_code": topic_code,
        "tool_name": tool_name,
        "stop_reason": getattr(msg, "stop_reason", None),
        "model": getattr(msg, "model", None),
        "usage": _usage_dict(getattr(msg, "usage", None)),
        "content": blocks,
    }
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )
    log.error("knowledge parse failed for %s/%s — raw response -> %s",
              topic_code, tool_name, path)
    return str(path)


class KnowledgeAgent(Protocol):
    name: str
    model: str | None
    prompt_version: str

    def extract(self, request: KnowledgeRequest) -> KnowledgeExtraction: ...


# --------------------------------------------------------------------------- #
# Stub

_VERB = re.compile(r"\b(oblicz|rozwiąż|wyznacz|wykaż|uzasadnij|zapisz)\b", re.I)


class StubKnowledgeAgent:
    """Offline, deterministic. Not a model — enough structure to exercise the
    persistence + yield report without the network."""

    name = "stub"
    model = None
    prompt_version = PROMPT_VERSION

    def extract(self, request: KnowledgeRequest) -> KnowledgeExtraction:
        out = KnowledgeExtraction()
        if not request.exercises:
            out.flags.append(FlagOut(
                kind="GAP", item_kind="all",
                detail=f"no exercises mapped to {request.topic_code}",
            ))
            return out
        ex = request.exercises[0]
        out.concepts.append(ConceptOut(
            name=request.topic_name[:80],
            description=f"exercised by Zadanie {ex.number}",
            from_exercises=[ex.number], evidence=ex.text[:200],
        ))
        if _VERB.search(" ".join(e.text for e in request.exercises)):
            out.methods.append(MethodOut(
                name=f"procedure for {request.topic_code}",
                when_to_use="see exercises", steps=["identify given", "apply", "verify"],
                from_exercises=[ex.number], evidence=ex.text[:200],
            ))
        # the stub emits two misconceptions: one inferred from an exercise
        # (AGENT_INFERENCE, keeps its citation) and one it cannot source
        # (UNSOURCED) — enough to exercise both flag paths offline.
        out.misconceptions.append(MisconceptionOut(
            name=f"common slip on {request.topic_code}",
            incorrect_reasoning="(stub)", correct_reasoning="(stub)",
            source_kind=MisconceptionSource.AGENT_INFERENCE,
            from_exercises=[ex.number], evidence="stub inference from exercise structure",
        ))
        out.misconceptions.append(MisconceptionOut(
            name=f"textbook slip on {request.topic_code}",
            incorrect_reasoning="(stub)", correct_reasoning="(stub)",
            source_kind=MisconceptionSource.UNSOURCED,
            from_exercises=[], evidence="stub: a known error with nothing in the material",
        ))
        return out


# --------------------------------------------------------------------------- #
# Claude

_SYSTEM_BASE = """\
You extract a structured knowledge spec for ONE Polish Matura mathematics \
curriculum requirement, from the material provided: the requirement text and a \
set of exam exercises that test it, each with its marking scheme (Zasady \
oceniania) where available.

Extraction is done in two passes. THIS pass covers only {scope}. Do not emit \
anything outside that set in this call — the other items are collected \
separately.
"""

_SYSTEM_STRUCTURE = _SYSTEM_BASE.format(scope="concepts, formulas, methods") + """
Hard rules:
* Use only what is in the provided material. Do not add facts, formulas or \
methods from your own knowledge that the material does not show.
* Every item lists `from_exercises` (the Zadanie numbers it is drawn from) and \
a short `evidence` quote or paraphrase from that material.
* If two sources disagree, emit a flag with kind "CONFLICT" carrying both \
readings; do not choose.
* If the material is missing something the requirement clearly needs, emit a \
flag with kind "GAP"; do not fill it from memory.

Call record_structure exactly once.
"""

_SYSTEM_PEDAGOGY = _SYSTEM_BASE.format(
    scope="worked examples, learning objectives, misconceptions"
) + """
Hard rules for examples and objectives:
* Use only what is in the provided material. Every item lists `from_exercises` \
and a short `evidence` quote or paraphrase. Missing information -> a GAP flag, \
not a filled gap; disagreement -> a CONFLICT flag.

Misconceptions are different, and the rule is the opposite: do NOT suppress \
them. Exam papers do not state student errors outright, so a "material-supported \
only" rule would return almost nothing — and that is worse than useless. \
Instead: list the real, common student errors on THIS requirement (aim for 3–6), \
and label each honestly with `source_kind`. A human approves every misconception \
in the dashboard before it is used — that review IS the verification step, so an \
inferred misconception is acceptable as long as it is labelled as one.

* MARKING_SCHEME — a partial-credit / "0 pkt jeśli…" rule in a Zasady oceniania \
block. Put the task number in `from_exercises`.
* INFORMATOR — CKE informator commentary (not present in the material yet).
* DISTRACTOR_INFERENCE — a wrong option in a multiple-choice / true-false task \
is built to catch this error. Name the task in `from_exercises` and the \
option(s) in `distractor` (e.g. "B and D", "C: 20000 · 1,06"). Prefer this over \
AGENT_INFERENCE whenever a distractor fits — it is the strongest source here.
* AGENT_INFERENCE — you are inferring the error from an open exercise's \
structure or its marking scheme, with no single distractor to point at. Name \
the exercise in `from_exercises` and say why in `evidence`. This is fine.
* UNSOURCED — a real student error you are confident about, but nothing in the \
material points to it. Still emit it, labelled UNSOURCED. Do not drop it.

Never withhold a misconception because you cannot cite it. A missing item helps \
nobody; a labelled inference gets reviewed. Only genuine non-errors should be \
left out.

Call record_pedagogy exactly once.
"""

_TOOL_STRUCTURE = {
    "name": "record_structure",
    "description": "Record the concepts, formulas and methods for the requirement.",
    "input_schema": _StructureExtraction.model_json_schema(),
}
_TOOL_PEDAGOGY = {
    "name": "record_pedagogy",
    "description": "Record the worked examples, objectives and misconceptions.",
    "input_schema": _PedagogyExtraction.model_json_schema(),
}


class ClaudeKnowledgeAgent:
    name = "claude"
    prompt_version = PROMPT_VERSION

    # how many times one _call may be re-sampled past a <parameter> malformation
    MALFORMED_RETRIES = 2

    def __init__(
        self, *, model: str = "claude-opus-5", max_tokens: int = 32000,
        thinking: bool = True,
    ) -> None:
        self.model = model
        self.max_tokens = max_tokens
        self.thinking = thinking
        self._client = None
        self.last_usage = None
        self.malformed_retries = 0  # <parameter> re-samples this extract() call

    def _client_lazy(self):
        if self._client is None:
            import anthropic

            from zaspro.config import get_settings

            key = get_settings().anthropic_api_key
            self._client = (
                anthropic.Anthropic(api_key=key) if key else anthropic.Anthropic()
            )
        return self._client

    def preflight(self) -> str:
        msg = self._client_lazy().messages.create(
            model=self.model, max_tokens=1,
            messages=[{"role": "user", "content": "ok"}],
        )
        return getattr(msg, "model", self.model)

    def _user_block(self, req: KnowledgeRequest) -> str:
        lines = [
            f"REQUIREMENT {req.topic_code}: {req.topic_name}",
            f"requirement text: {req.requirement_text or '—'}",
            "",
            f"EXERCISES ({len(req.exercises)}):",
        ]
        for e in req.exercises:
            lines.append(f"\n--- Zadanie {e.number}"
                         f"{f' (difficulty {e.difficulty})' if e.difficulty else ''}"
                         f"{f' [{e.points} pkt]' if e.points else ''} ---")
            lines.append(e.latex or e.text)
            if e.marking_scheme:
                lines.append(f"Zasady oceniania:\n{e.marking_scheme}")
        return "\n".join(lines)

    def _add_usage(self, u) -> None:
        if u is None:
            return
        self.last_usage["in"] += getattr(u, "input_tokens", 0) or 0
        self.last_usage["out"] += getattr(u, "output_tokens", 0) or 0
        self.last_usage["cache_read"] += getattr(u, "cache_read_input_tokens", 0) or 0
        self.last_usage["cache_write"] += getattr(u, "cache_creation_input_tokens", 0) or 0

    def _stream_once(self, request: KnowledgeRequest, system: str, tool: dict, tool_name: str):
        client = self._client_lazy()
        _cache = {"type": "ephemeral"}
        tc = request.topic_code
        kw: dict = dict(
            model=self.model,
            max_tokens=self.max_tokens,
            system=[{"type": "text", "text": system, "cache_control": _cache}],
            tools=[{**tool, "cache_control": _cache}],
            messages=[{"role": "user", "content": self._user_block(request)}],
        )
        if self.thinking:
            kw["thinking"] = {"type": "adaptive"}
        # Stream, don't `create`: a large max_tokens pushes the worst-case
        # response time past 10 minutes and the SDK refuses a non-streaming call.
        try:
            with client.messages.stream(**kw) as stream:
                msg = stream.get_final_message()
        except PermanentJobError:
            raise
        except Exception as e:  # noqa: BLE001
            # 4xx other than 429 is deterministic (bad request, context length,
            # auth) — permanent. Connection errors, 429, 5xx, overload have no
            # status < 500 and propagate unwrapped so the worker retries them.
            status = getattr(e, "status_code", None)
            if status is not None and 400 <= status < 500 and status != 429:
                raise KnowledgeError(f"{tool_name} for {tc}: API {status} — {e}") from e
            raise
        self._add_usage(getattr(msg, "usage", None))
        return msg

    def _parse_call(self, msg, model_cls, tool_name: str, tc: str):
        # Fail loudly on truncation — never persist a partial spec as complete.
        if getattr(msg, "stop_reason", None) == "max_tokens":
            _dump_raw(tc, tool_name, msg)
            raise KnowledgeTruncated(
                f"{tool_name} hit max_tokens ({self.max_tokens}) for {tc}; "
                f"partial result discarded"
            )

        blocks = [
            b for b in (msg.content or [])
            if getattr(b, "type", None) == "tool_use" and getattr(b, "name", None) == tool_name
        ]
        if not blocks:
            path = _dump_raw(tc, tool_name, msg)
            raise KnowledgeError(
                f"{tool_name} for {tc}: no matching tool_use block "
                f"(stop_reason={getattr(msg, 'stop_reason', None)}); raw -> {path}"
            )

        data = blocks[0].input
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except json.JSONDecodeError as e:
                path = _dump_raw(tc, tool_name, msg)
                raise KnowledgeError(
                    f"{tool_name} for {tc}: tool input was a non-JSON string "
                    f"({e}); raw -> {path}"
                ) from e
        try:
            return model_cls.model_validate(data)
        except ValidationError as e:
            path = _dump_raw(tc, tool_name, msg)
            if _is_pseudo_syntax(e):
                # Claude emitted `<parameter name=…>` pseudo-syntax as a string
                # argument. Transient, sampling-dependent — re-sample, don't
                # unpack. Caller retries; the malformation is logged with the
                # topic so we can watch the rate.
                raise KnowledgeMalformed(
                    f"{tool_name} for {tc}: <parameter> pseudo-syntax in a tool "
                    f"argument; raw -> {path}"
                ) from e
            raise KnowledgeError(
                f"{tool_name} for {tc}: tool input failed the {model_cls.__name__} "
                f"schema; raw -> {path}\n{e}"
            ) from e

    def _call(self, request: KnowledgeRequest, system: str, tool: dict, model_cls, tool_name: str):
        tc = request.topic_code
        for attempt in range(self.MALFORMED_RETRIES + 1):
            msg = self._stream_once(request, system, tool, tool_name)
            try:
                return self._parse_call(msg, model_cls, tool_name, tc)
            except KnowledgeMalformed as e:
                self.malformed_retries += 1
                last = attempt == self.MALFORMED_RETRIES
                log.warning(
                    "MALFORMED_TOOL_CALL topic=%s tool=%s attempt=%d/%d%s :: %s",
                    tc, tool_name, attempt + 1, self.MALFORMED_RETRIES + 1,
                    " (giving up)" if last else " (re-sampling)", e,
                )
                if last:
                    raise KnowledgeError(
                        f"{tool_name} for {tc}: <parameter> malformation persisted "
                        f"across {attempt + 1} samples — failing the job"
                    ) from e
        raise AssertionError("unreachable")

    def extract(self, request: KnowledgeRequest) -> KnowledgeExtraction:
        # Two calls: structure (concepts/formulas/methods) then pedagogy
        # (examples/objectives/misconceptions). Neither response has to carry a
        # large topic's whole spec. Usage is summed across both.
        self.last_usage = {"in": 0, "out": 0, "cache_read": 0, "cache_write": 0}
        self.malformed_retries = 0
        struct: _StructureExtraction = self._call(
            request, _SYSTEM_STRUCTURE, _TOOL_STRUCTURE, _StructureExtraction, "record_structure"
        )
        peda: _PedagogyExtraction = self._call(
            request, _SYSTEM_PEDAGOGY, _TOOL_PEDAGOGY, _PedagogyExtraction, "record_pedagogy"
        )
        return KnowledgeExtraction(
            concepts=struct.concepts,
            formulas=struct.formulas,
            methods=struct.methods,
            examples=peda.examples,
            objectives=peda.objectives,
            misconceptions=peda.misconceptions,
            flags=[*struct.flags, *peda.flags],
        )


def default_agent() -> KnowledgeAgent:
    from zaspro.config import get_settings

    if get_settings().anthropic_api_key:
        return ClaudeKnowledgeAgent()
    return StubKnowledgeAgent()


_AGENT: KnowledgeAgent | None = None


def set_agent(agent: KnowledgeAgent | None) -> None:
    global _AGENT
    _AGENT = agent


def get_agent() -> KnowledgeAgent:
    return _AGENT if _AGENT is not None else default_agent()
