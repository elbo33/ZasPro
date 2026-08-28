"""A single-process worker loop. One job per transaction; granular retries."""

from __future__ import annotations

import logging
import time
import traceback
from collections.abc import Callable
from typing import Any

from sqlalchemy.orm import Session

from zaspro.db.base import session_scope
from zaspro.db.models import Job, JobStatus, JobType
from zaspro.jobs.errors import PermanentJobError
from zaspro.jobs.queue import claim_one

log = logging.getLogger("zaspro.jobs")

Handler = Callable[[Session, Job], "dict[str, Any] | None"]
HANDLERS: dict[JobType, Handler] = {}


def register(job_type: JobType) -> Callable[[Handler], Handler]:
    def deco(fn: Handler) -> Handler:
        if job_type in HANDLERS:
            raise RuntimeError(f"handler for {job_type} already registered")
        HANDLERS[job_type] = fn
        return fn

    return deco


class Worker:
    def __init__(self, poll_interval: float = 1.0) -> None:
        self.poll_interval = poll_interval

    def run_once(self) -> bool:
        """Process at most one job. Returns False when the queue is empty."""

        with session_scope() as s:
            job = claim_one(s)
            job_id = job.id if job else None
            job_type = job.job_type if job else None
        if job_id is None:
            return False

        handler = HANDLERS.get(job_type)
        if handler is None:
            with session_scope() as s:
                j = s.get(Job, job_id)
                j.status = JobStatus.FAILED
                j.error = f"no handler registered for {job_type}"
            return True

        try:
            with session_scope() as s:
                j = s.get(Job, job_id)
                output = handler(s, j)
                j.status = JobStatus.SUCCEEDED
                j.output = output
        except PermanentJobError:
            # deterministic — do not spend the remaining attempts (or, for
            # agent jobs, the money) re-running the same broken call.
            tb = traceback.format_exc()
            log.warning("job %s (%s) failed permanently:\n%s", job_id, job_type, tb)
            with session_scope() as s:
                j = s.get(Job, job_id)
                j.error = tb[-4000:]
                j.status = JobStatus.FAILED
        except Exception:  # noqa: BLE001 - transient; retry up to max_attempts
            tb = traceback.format_exc()
            log.warning("job %s (%s) failed:\n%s", job_id, job_type, tb)
            with session_scope() as s:
                j = s.get(Job, job_id)
                j.error = tb[-4000:]
                j.status = (
                    JobStatus.PENDING if j.attempts < j.max_attempts else JobStatus.FAILED
                )
        return True

    def drain(self, max_iterations: int = 10_000) -> int:
        """Run until the queue is empty (for scripts and tests). Returns count."""

        done = 0
        for _ in range(max_iterations):
            if not self.run_once():
                return done
            done += 1
        raise RuntimeError(f"drain() hit {max_iterations} iterations — a job may be re-queueing")

    def run_forever(self) -> None:  # pragma: no cover - operational loop
        while True:
            if not self.run_once():
                time.sleep(self.poll_interval)
