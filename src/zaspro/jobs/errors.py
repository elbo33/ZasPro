"""Failure classification for the worker.

A handler raises `PermanentJobError` (or a subclass) for a deterministic
failure — a schema-invalid model response, a truncated response, bad input.
Retrying it would fail identically and, for agent jobs, cost money on every
attempt. The worker marks such a job FAILED at once instead of requeuing it up
to `max_attempts`.

Anything else — a raised `Exception` that is not a `PermanentJobError` — is
treated as transient (network blip, rate limit, 5xx, overload) and retried.
"""

from __future__ import annotations


class PermanentJobError(Exception):
    """A deterministic job failure. The worker fails the job without retrying."""
