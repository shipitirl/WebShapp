"""Filesystem + Redis watcher that orchestrates the real-time pipeline."""
from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Optional

from redis.asyncio import Redis
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from backend import ws
from backend.cache import append_stream, cache_live_packet, cache_winprob, publish_update
from backend.deps import REDIS_DSN
from backend.schemas import LivePacket
from engine.meta_model import meta_model

logger = logging.getLogger(__name__)

DATA_DIR = Path("data/nfl_predictions")


class ParquetEventHandler(FileSystemEventHandler):
    """Reload DuckDB views when new parquet files arrive."""

    def __init__(self, callback) -> None:
        self._callback = callback

    def on_created(self, event):  # type: ignore[override]
        if event.is_directory or not event.src_path.endswith(".parquet"):
            return
        logger.info("Detected new parquet file %s", event.src_path)
        asyncio.run_coroutine_threadsafe(self._callback(), asyncio.get_event_loop())


async def handle_packet(redis: Redis, raw: bytes) -> None:
    payload = json.loads(raw)
    packet = LivePacket.model_validate(payload)
    await cache_live_packet(redis, packet)
    msg = meta_model.update(packet)
    await cache_winprob(redis, msg)
    await publish_update(redis, msg)
    await append_stream(redis, packet)
    await ws.manager.broadcast({"gid": msg.gid, "p_win": msg.p_win, "ts": msg.ts, "explain": msg.explain})


async def redis_listener() -> None:
    redis = Redis.from_url(REDIS_DSN, encoding="utf-8", decode_responses=False)
    pubsub = redis.pubsub()
    await pubsub.subscribe("shap_updates")
    logger.info("Watcher subscribed to shap_updates")
    try:
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue
            await handle_packet(redis, message["data"])
    finally:
        await pubsub.close()
        await redis.aclose()


async def reload_duckdb_view() -> None:
    from backend.deps import get_duckdb
    from backend.queries import ensure_view

    conn = get_duckdb()
    ensure_view(conn)
    logger.info("Refreshed DuckDB view shap_live")


async def run_watcher(stop_event: Optional[asyncio.Event] = None) -> None:
    observer = Observer()
    handler = ParquetEventHandler(reload_duckdb_view)
    observer.schedule(handler, str(DATA_DIR), recursive=True)
    observer.start()
    logger.info("Watcher observing %s", DATA_DIR)
    try:
        await redis_listener()
    finally:
        observer.stop()
        observer.join()
        if stop_event:
            stop_event.set()


if __name__ == "__main__":
    asyncio.run(run_watcher())
