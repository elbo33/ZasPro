"""The Mapping Agent (SPEC §12 agent 2) and its job handler.

    from zaspro.mapping import map_chunk, map_document, StubMappingAgent

Importing this package registers the `MAP_CHUNK` job handler.
"""

from zaspro.mapping.agent import (
    AUTO_APPROVE_THRESHOLD,
    DEFAULT_AUDIT_SAMPLE_RATE,
    PROMPT_VERSION,
    ClaudeMappingAgent,
    MappingAgent,
    MappingError,
    MappingRequest,
    MappingResult,
    StubMappingAgent,
    TopicRef,
    default_agent,
)
from zaspro.mapping.handler import (
    candidate_topics,
    handle_map_chunk,
    map_chunk,
    map_document,
    set_agent,
)

__all__ = [
    "AUTO_APPROVE_THRESHOLD",
    "DEFAULT_AUDIT_SAMPLE_RATE",
    "PROMPT_VERSION",
    "ClaudeMappingAgent",
    "MappingAgent",
    "MappingError",
    "MappingRequest",
    "MappingResult",
    "StubMappingAgent",
    "TopicRef",
    "default_agent",
    "candidate_topics",
    "handle_map_chunk",
    "map_chunk",
    "map_document",
    "set_agent",
]
