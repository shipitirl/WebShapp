"""Lightweight background scheduler for periodic jobs."""
from __future__ import annotations

import asyncio
import contextlib
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Dict


@dataclass
class Job:
    name: str
    interval: float
    coro: Callable[[], Awaitable[None]]
    _task: asyncio.Task | None = None

    async def run(self) -> None:
        while True:
            await self.coro()
            await asyncio.sleep(self.interval)


class Scheduler:
    """Asyncio-based scheduler with start/stop controls."""

    def __init__(self) -> None:
        self._jobs: Dict[str, Job] = {}
        self._running = False

    def add_job(self, name: str, interval: float, coro: Callable[[], Awaitable[None]]) -> None:
        self._jobs[name] = Job(name=name, interval=interval, coro=coro)

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        loop = asyncio.get_event_loop()
        for job in self._jobs.values():
            job._task = loop.create_task(job.run())

    async def stop(self) -> None:
        if not self._running:
            return
        for job in self._jobs.values():
            if job._task:
                job._task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await job._task
        self._running = False


scheduler = Scheduler()
