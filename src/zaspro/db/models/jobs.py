"""The job queue (SPEC §15). A Postgres table plus a worker loop — no Celery,
Redis or RabbitMQ until the simple version is provably insufficient (SPEC §3).

Every row records how it was produced (model, prompt_version, pipeline_version)
so any downstream row is traceable. Retries are granular and per-row.
"""

from __future__ import annotations

import enum
from typing import Any

from sqlalchemy import Enum, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from zaspro.db.base import Base, TimestampMixin


class JobType(str, enum.Enum):
    INGEST_DOCUMENT = "INGEST_DOCUMENT"
    CONVERT_DOCX = "CONVERT_DOCX"
    EXTRACT_MEDIA = "EXTRACT_MEDIA"
    RENDER_VECTOR_FIGURE = "RENDER_VECTOR_FIGURE"
    SEGMENT_EXERCISES = "SEGMENT_EXERCISES"
    NORMALISE_LATEX = "NORMALISE_LATEX"
    EXTRACT_PDF_TEXT = "EXTRACT_PDF_TEXT"
    CHUNK_DOCUMENT = "CHUNK_DOCUMENT"
    CLASSIFY_CHUNK = "CLASSIFY_CHUNK"
    MAP_CHUNK = "MAP_CHUNK"
    EXTRACT_KNOWLEDGE = "EXTRACT_KNOWLEDGE"
    MERGE_CANDIDATES = "MERGE_CANDIDATES"
    VERIFY_FORMULA = "VERIFY_FORMULA"
    GENERATE_EXERCISE = "GENERATE_EXERCISE"
    VERIFY_EXERCISE = "VERIFY_EXERCISE"
    ASSEMBLE_KNOWLEDGE_SPEC = "ASSEMBLE_KNOWLEDGE_SPEC"
    GENERATE_EPISODE_PLAN = "GENERATE_EPISODE_PLAN"
    GENERATE_SCENE_PLAN = "GENERATE_SCENE_PLAN"
    RUN_QA = "RUN_QA"


class JobStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class Job(Base, TimestampMixin):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    job_type: Mapped[JobType] = mapped_column(
        Enum(JobType, name="job_type", native_enum=False, validate_strings=True)
    )
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, name="job_status", native_enum=False, validate_strings=True),
        default=JobStatus.PENDING,
        index=True,
    )
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)

    input: Mapped[Any] = mapped_column(JSONB, default=dict)
    output: Mapped[Any | None] = mapped_column(JSONB)
    error: Mapped[str | None] = mapped_column(Text)

    model: Mapped[str | None] = mapped_column(String(64))
    prompt_version: Mapped[str | None] = mapped_column(String(32))
    pipeline_version: Mapped[str | None] = mapped_column(String(32))
