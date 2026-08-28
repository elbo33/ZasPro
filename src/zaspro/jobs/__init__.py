"""Postgres-backed job queue and a worker loop (SPEC §3, §15).

    from zaspro.jobs import enqueue, Worker, register

No external broker. `SELECT … FOR UPDATE SKIP LOCKED` is the queue.
"""

from zaspro.jobs.errors import PermanentJobError
from zaspro.jobs.queue import enqueue
from zaspro.jobs.worker import HANDLERS, Worker, register

__all__ = ["enqueue", "Worker", "register", "HANDLERS", "PermanentJobError"]
