"""Register background jobs."""
from __future__ import annotations

from .scheduler import scheduler
from .drift import drift_job

scheduler.add_job("drift", interval=300.0, coro=drift_job)
