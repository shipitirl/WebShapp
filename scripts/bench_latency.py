"""Benchmark end-to-end latency from Redis publish to websocket."""
from __future__ import annotations

import argparse
import asyncio
import json
import time
from statistics import mean
from typing import List

import websockets
from redis.asyncio import Redis

from backend.cache import PUBSUB_CHANNEL


async def measure_once(redis: Redis, packet: dict, ws_url: str) -> float:
    start = time.perf_counter()
    async with websockets.connect(ws_url) as websocket:
        await redis.publish(PUBSUB_CHANNEL, json.dumps(packet))
        await websocket.recv()
    end = time.perf_counter()
    return (end - start) * 1000


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ws", default="ws://localhost:8000/ws/live")
    parser.add_argument("--runs", type=int, default=5)
    args = parser.parse_args()

    redis = Redis.from_url("redis://localhost:6379/0", encoding="utf-8", decode_responses=False)
    packet = {
        "gid": "demo",
        "ts": int(time.time() * 1000),
        "y_pred": 0.5,
        "state": {"q": 1, "time_left": 900, "down": 1, "dist": 10, "yardline": 25, "to_a": 3, "to_b": 3, "score_a": 0, "score_b": 0},
        "shap": [{"f": "QB_pressure_rate", "s": 0.1}, {"f": "WR_sep", "s": -0.05}],
        "model_version": "v0",
    }
    latencies: List[float] = []
    try:
        for _ in range(args.runs):
            latencies.append(await measure_once(redis, packet, args.ws))
    finally:
        await redis.aclose()

    print(f"Average latency: {mean(latencies):.2f} ms")


if __name__ == "__main__":
    asyncio.run(main())
