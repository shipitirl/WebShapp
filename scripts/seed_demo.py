"""Replay a historical game to seed the live engine."""
from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from redis.asyncio import Redis

from backend.cache import PUBSUB_CHANNEL


async def publish_packets(path: Path, speed: float, redis: Redis, gid: str) -> None:
    with path.open("r", encoding="utf-8") as fh:
        packets = [json.loads(line) for line in fh]
    for packet in packets:
        packet["gid"] = gid
        await redis.publish(PUBSUB_CHANNEL, json.dumps(packet))
        await asyncio.sleep(max(packet.get("sleep", 1.0) / speed, 0.0))


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gid", required=True)
    parser.add_argument("--input", default="scripts/demo_packets.jsonl")
    parser.add_argument("--speed", type=float, default=1.0)
    args = parser.parse_args()

    redis = Redis.from_url("redis://localhost:6379/0", encoding="utf-8", decode_responses=False)
    try:
        await publish_packets(Path(args.input), args.speed, redis, args.gid)
    finally:
        await redis.aclose()


if __name__ == "__main__":
    asyncio.run(main())
