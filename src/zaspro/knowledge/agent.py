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
import re
from typing import Protocol

from pydantic import BaseModel, Field

from zaspro.db.models import MisconceptionSource

PROMPT_VERSION = "m4-know-v3"  # v3: stop suppressing misconceptions — emit + label + flag, never withhold


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


class KnowledgeError(RuntimeError):
    pass


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

_SYSTEM = """\
You extract a structured knowledge spec for ONE Polish Matura mathematics \
curriculum requirement, from the material provided: the requirement text and a \
set of exam exercises that test it, each with its marking scheme (Zasady \
oceniania) where available.

Hard rules for concepts, formulas, methods, examples, objectives:
* Use only what is in the provided material. Do not add facts, formulas or \
methods from your own knowledge that the material does not show.
* Every item lists `from_exercises` (the Zadanie numbers it is drawn from) and \
a short `evidence` quote or paraphrase from that material.
* If two sources disagree, emit a flag with kind "CONFLICT" carrying both \
readings; do not choose.
* If the material is missing something the requirement clearly needs, emit a \
flag with kind "GAP"; do not fill it from memory.

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

Call record_knowledge exactly once.
"""

_TOOL = {
    "name": "record_knowledge",
    "description": "Record the extracted knowledge spec for the requirement.",
    "input_schema": KnowledgeExtraction.model_json_schema(),
}


class ClaudeKnowledgeAgent:
    name = "claude"
    prompt_version = PROMPT_VERSION

    def __init__(self, *, model: str = "claude-opus-5", max_tokens: int = 32000) -> None:
        self.model = model
        self.max_tokens = max_tokens
        self._client = None
        self.last_usage = None

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

    def extract(self, request: KnowledgeRequest) -> KnowledgeExtraction:
        client = self._client_lazy()
        _cache = {"type": "ephemeral"}
        # Stream, don't `create`: at max_tokens=32000 the worst-case response
        # time exceeds 10 minutes and the SDK refuses a non-streaming call
        # outright. `get_final_message()` accumulates the whole response —
        # usage and tool_use block included — so the rest of this method is
        # unchanged. Keep 32k: 16k was truncating the large topics.
        with client.messages.stream(
            model=self.model,
            max_tokens=self.max_tokens,
            thinking={"type": "adaptive"},
            system=[{"type": "text", "text": _SYSTEM, "cache_control": _cache}],
            tools=[{**_TOOL, "cache_control": _cache}],
            messages=[{"role": "user", "content": self._user_block(request)}],
        ) as stream:
            msg = stream.get_final_message()
        u = getattr(msg, "usage", None)
        self.last_usage = {
            "in": getattr(u, "input_tokens", 0) or 0,
            "out": getattr(u, "output_tokens", 0) or 0,
            "cache_read": getattr(u, "cache_read_input_tokens", 0) or 0,
            "cache_write": getattr(u, "cache_creation_input_tokens", 0) or 0,
        }
        for block in msg.content:
            if getattr(block, "type", None) == "tool_use" and block.name == "record_knowledge":
                data = block.input
                if isinstance(data, str):
                    data = json.loads(data)
                return KnowledgeExtraction.model_validate(data)
        raise KnowledgeError("model did not call record_knowledge")


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
