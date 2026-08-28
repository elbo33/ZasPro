"""The Knowledge Agent (SPEC §12 agent 3) — writes one teaching section.

The agent writes a section the way a textbook chapter would: definitions and the
concepts a student needs, the formulas with their conditions, the standard
methods and when to use them, worked examples that build in difficulty, learning
objectives, and the mistakes students actually make on this material. Written
from knowledge of Polish Matura podstawowa mathematics, scoped by the section's
requirement codes.

Exercises are not a source. There is no aggregation, no citation, no provenance.
The human approves every section spec in the dashboard — the only verification.

`StubSectionAgent` runs the whole path offline; `ClaudeSectionAgent`
(`claude-opus-5`) is used only from a command the user runs. One call, one tool.
If it fails, the job fails and the run notes it — nothing to retry.
"""

from __future__ import annotations

import json
from typing import Protocol

from pydantic import BaseModel, Field

PROMPT_VERSION = "m4-sec-v1"


class RequirementCtx(BaseModel):
    code: str
    text: str


class SectionRequest(BaseModel):
    slug: str
    name: str
    scope: str
    requirements: list[RequirementCtx]


class ConceptOut(BaseModel):
    name: str
    definition: str
    explanation: str | None = None       # why it matters / how to think about it
    difficulty: int | None = Field(None, ge=1, le=5)


class FormulaOut(BaseModel):
    name: str
    latex: str
    conditions: str | None = None        # when it applies
    note: str | None = None


class MethodOut(BaseModel):
    name: str
    when_to_use: str
    steps: list[str] = Field(default_factory=list)


class ExampleOut(BaseModel):
    statement: str
    worked_solution: str
    difficulty: int | None = Field(None, ge=1, le=5)


class MisconceptionOut(BaseModel):
    name: str
    incorrect_reasoning: str
    correct_reasoning: str
    severity: int | None = Field(None, ge=1, le=5)


class ObjectiveOut(BaseModel):
    statement: str
    bloom_level: str | None = None


class SectionSpecOut(BaseModel):
    concepts: list[ConceptOut] = Field(default_factory=list)
    formulas: list[FormulaOut] = Field(default_factory=list)
    methods: list[MethodOut] = Field(default_factory=list)
    examples: list[ExampleOut] = Field(default_factory=list)
    misconceptions: list[MisconceptionOut] = Field(default_factory=list)
    objectives: list[ObjectiveOut] = Field(default_factory=list)


class KnowledgeError(RuntimeError):
    """The agent call failed (no tool call, unparseable output, API error). The
    job fails; the run notes it and moves on."""


class KnowledgeAgent(Protocol):
    name: str
    model: str | None
    prompt_version: str

    def write(self, request: SectionRequest) -> SectionSpecOut: ...


# --------------------------------------------------------------------------- #
# Stub

class StubSectionAgent:
    """Offline, deterministic. Enough structure to exercise persistence."""

    name = "stub"
    model = None
    prompt_version = PROMPT_VERSION

    def write(self, request: SectionRequest) -> SectionSpecOut:
        out = SectionSpecOut()
        out.concepts.append(ConceptOut(
            name=request.name[:80],
            definition=f"core idea of the section '{request.name}'",
            explanation=request.scope[:200], difficulty=2,
        ))
        out.formulas.append(FormulaOut(
            name="stub formula", latex="a^2 + b^2 = c^2", conditions="stub",
        ))
        out.methods.append(MethodOut(
            name="stub method", when_to_use="see scope",
            steps=["identify given", "apply", "check"],
        ))
        out.examples.append(ExampleOut(
            statement="stub example", worked_solution="stub solution", difficulty=1,
        ))
        out.examples.append(ExampleOut(
            statement="harder stub example", worked_solution="stub solution", difficulty=3,
        ))
        out.misconceptions.append(MisconceptionOut(
            name=f"common slip on {request.slug}",
            incorrect_reasoning="(stub)", correct_reasoning="(stub)", severity=2,
        ))
        out.objectives.append(ObjectiveOut(
            statement=f"student can work the tasks in '{request.name}'",
            bloom_level="apply",
        ))
        return out


# --------------------------------------------------------------------------- #
# Claude

_SYSTEM = """\
You write the knowledge spec for ONE section of a Polish Matura ("podstawowy") \
mathematics course, the way a good textbook chapter would. You are given the \
section name, a scope statement, and the official requirement(s) it covers.

Write from your own knowledge of the subject, pitched at Matura podstawowa \
level, bounded by the scope. Produce:
* concepts — every definition and idea a student needs, each with a short \
explanation of how to think about it;
* formulas — with the conditions under which they hold;
* methods — the standard procedures, each with when to use it and ordered steps;
* examples — worked in full, ordered so they build in difficulty (2-5 of them);
* misconceptions — the mistakes students actually make on this material, each \
with the wrong reasoning and the correction;
* objectives — what a student should be able to do, at the right Bloom level.

Do not reference exam papers, exercises or marking schemes — none are provided \
and none are needed. A section is written to the same depth whether or not exam \
tasks exist for it. Aim for a spec rich enough to support four teaching \
episodes.

Call record_section exactly once.
"""

_TOOL = {
    "name": "record_section",
    "description": "Record the knowledge spec for this section.",
    "input_schema": SectionSpecOut.model_json_schema(),
}


class ClaudeSectionAgent:
    name = "claude"
    prompt_version = PROMPT_VERSION

    def __init__(self, *, model: str = "claude-opus-5", max_tokens: int = 64000) -> None:
        self.model = model
        self.max_tokens = max_tokens
        self._client = None
        self.last_usage: dict | None = None

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

    def _user_block(self, req: SectionRequest) -> str:
        lines = [
            f"SECTION: {req.name}",
            f"scope: {req.scope}",
            "",
            "covers these official requirements:",
        ]
        for r in req.requirements:
            lines.append(f"  {r.code}: {r.text}")
        return "\n".join(lines)

    def write(self, request: SectionRequest) -> SectionSpecOut:
        client = self._client_lazy()
        _cache = {"type": "ephemeral"}
        try:
            with client.messages.stream(
                model=self.model,
                max_tokens=self.max_tokens,
                thinking={"type": "adaptive"},
                system=[{"type": "text", "text": _SYSTEM, "cache_control": _cache}],
                tools=[{**_TOOL, "cache_control": _cache}],
                messages=[{"role": "user", "content": self._user_block(request)}],
            ) as stream:
                msg = stream.get_final_message()
        except Exception as e:  # noqa: BLE001 - the run notes the failure and moves on
            raise KnowledgeError(f"{request.slug}: API call failed ({type(e).__name__}): {e}") from e

        u = getattr(msg, "usage", None)
        self.last_usage = {
            "in": getattr(u, "input_tokens", 0) or 0,
            "out": getattr(u, "output_tokens", 0) or 0,
            "cache_read": getattr(u, "cache_read_input_tokens", 0) or 0,
            "cache_write": getattr(u, "cache_creation_input_tokens", 0) or 0,
        }
        for block in msg.content:
            if getattr(block, "type", None) == "tool_use" and block.name == "record_section":
                data = block.input
                if isinstance(data, str):
                    data = json.loads(data)
                try:
                    return SectionSpecOut.model_validate(data)
                except Exception as e:  # noqa: BLE001
                    raise KnowledgeError(
                        f"{request.slug}: record_section output did not match the schema "
                        f"(stop_reason={getattr(msg, 'stop_reason', None)}): {e}"
                    ) from e
        raise KnowledgeError(
            f"{request.slug}: model did not call record_section "
            f"(stop_reason={getattr(msg, 'stop_reason', None)})"
        )


def default_agent() -> KnowledgeAgent:
    from zaspro.config import get_settings

    if get_settings().anthropic_api_key:
        return ClaudeSectionAgent()
    return StubSectionAgent()


_AGENT: KnowledgeAgent | None = None


def set_agent(agent: KnowledgeAgent | None) -> None:
    global _AGENT
    _AGENT = agent


def get_agent() -> KnowledgeAgent:
    return _AGENT if _AGENT is not None else default_agent()
