"""Job queue + worker: success, granular retry, failure recording (SPEC §15).

The worker commits in its own sessions, so tests observe real rows; the `db`
fixture truncates every table between tests for isolation.
"""

import pytest

from zaspro.db.models import Job, JobStatus, JobType
from zaspro.jobs import PermanentJobError, Worker, enqueue
from zaspro.jobs.worker import HANDLERS


@pytest.fixture
def handlers():
    """Snapshot the handler registry; restore it after the test."""

    saved = dict(HANDLERS)
    try:
        yield HANDLERS
    finally:
        HANDLERS.clear()
        HANDLERS.update(saved)


def test_a_job_runs_and_records_output(db, handlers):
    calls = []
    handlers[JobType.RUN_QA] = lambda s, j: (calls.append(j.input), {"ok": True})[1]

    enqueue(db, JobType.RUN_QA, {"x": 1})
    db.commit()

    assert Worker().run_once() is True
    assert Worker().run_once() is False  # queue drained

    db.expire_all()
    job = db.query(Job).one()
    assert job.status == JobStatus.SUCCEEDED
    assert job.output == {"ok": True}
    assert job.attempts == 1
    assert calls == [{"x": 1}]


def test_failing_job_retries_then_fails(db, handlers):
    seen = []

    def boom(s, j):
        seen.append(j.attempts)
        raise RuntimeError("kaboom")

    handlers[JobType.RUN_QA] = boom
    enqueue(db, JobType.RUN_QA, {}, max_attempts=2)
    db.commit()

    w = Worker()
    assert w.run_once() is True  # attempt 1 -> requeued PENDING
    assert w.run_once() is True  # attempt 2 -> FAILED
    assert w.run_once() is False

    db.expire_all()
    job = db.query(Job).one()
    assert job.status == JobStatus.FAILED
    assert job.attempts == 2
    assert "kaboom" in job.error
    assert seen == [1, 2]


def test_permanent_job_error_fails_without_retrying(db, handlers):
    seen = []

    def boom(s, j):
        seen.append(j.attempts)
        raise PermanentJobError("deterministic — schema-invalid model response")

    handlers[JobType.RUN_QA] = boom
    enqueue(db, JobType.RUN_QA, {}, max_attempts=3)
    db.commit()

    w = Worker()
    assert w.run_once() is True   # attempt 1 -> FAILED immediately
    assert w.run_once() is False  # not requeued

    db.expire_all()
    job = db.query(Job).one()
    assert job.status == JobStatus.FAILED
    assert job.attempts == 1               # did NOT burn all 3
    assert seen == [1]
    assert "deterministic" in job.error


def test_unknown_job_type_fails_cleanly(db, handlers):
    handlers.pop(JobType.RUN_QA, None)
    enqueue(db, JobType.RUN_QA, {})
    db.commit()

    assert Worker().run_once() is True
    db.expire_all()
    job = db.query(Job).one()
    assert job.status == JobStatus.FAILED
    assert "no handler" in job.error
