"""Dependency wiring for shared infrastructure clients."""
from __future__ import annotations

import contextlib
import functools
from pathlib import Path
from typing import AsyncIterator, Callable

import duckdb
from fastapi import Depends
from redis.asyncio import Redis


DUCKDB_PATH = Path("data/live.duckdb")
REDIS_DSN = "redis://localhost:6379/0"


@functools.lru_cache(maxsize=1)
def get_duckdb() -> duckdb.DuckDBPyConnection:
    """Return a process-wide DuckDB connection."""

    conn = duckdb.connect(str(DUCKDB_PATH))
    conn.execute("PRAGMA busy_timeout=5000;")
    return conn


async def get_redis() -> AsyncIterator[Redis]:
    """Yield an asyncio Redis client."""

    client = Redis.from_url(REDIS_DSN, encoding="utf-8", decode_responses=False)
    try:
        yield client
    finally:
        await client.aclose()


RedisDep = Depends(get_redis)
DuckDBDep = Depends(get_duckdb)


@contextlib.contextmanager
def redis_pipeline(redis: Redis) -> Callable[[], None]:
    """Context manager that yields a Redis pipeline executor."""

    pipe = redis.pipeline()
    try:
        yield pipe
    finally:
        pipe.reset()
