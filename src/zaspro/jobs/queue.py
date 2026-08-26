"""Enqueue and claim jobs."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from zaspro.db.models import Job, JobStatus, JobType

PIPELINE_VERSION = "m2"


def enqueue(
    session: Session,
    job_type: JobType,
    payload: dict[str, Any] | None = None,
    *,
    max_attempts: int = 3,
    model: str | None = None,
    prompt_version: str | None = None,
    pipeline_version: str = PIPELINE_VERSION,
) -> Job:
    job = Job(
        job_type=job_type,
        input=payload or {},
        max_attempts=max_attempts,
        model=model,
        prompt_version=prompt_version,
        pipeline_version=pipeline_version,
    )
    session.add(job)
    session.flush()
    return job


def claim_one(session: Session) -> Job | None:
    """Lock and mark one pending job RUNNING. Concurrent workers skip it."""

    stmt = (
        select(Job)
        .where(Job.status == JobStatus.PENDING)
        .order_by(Job.id)
        .with_for_update(skip_locked=True)
        .limit(1)
    )
    job = session.scalars(stmt).first()
    if job is None:
        return None
    job.status = JobStatus.RUNNING
    job.attempts += 1
    job.error = None
    session.flush()
    return job
