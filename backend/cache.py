"""Redis cache helpers for live win probability state."""
from __future__ import annotations

import json
from typing import Any, Dict, Iterable, Tuple

from redis.asyncio import Redis

from .schemas import LivePacket, WinProbMsg

WIN_PROB_KEY = "game:{gid}:winprob"
LAST_SHAP_KEY = "game:{gid}:last_shap"
TTL_SECONDS = 48 * 3600
PUBSUB_CHANNEL = "shap_updates"
STREAM_KEY = "shap_stream"


def _key(template: str, gid: str) -> str:
    return template.format(gid=gid)


async def cache_live_packet(redis: Redis, packet: LivePacket) -> None:
    """Persist the latest raw packet in Redis for reference."""

    payload = json.dumps(packet.model_dump(mode="json"))
    await redis.setex(_key(LAST_SHAP_KEY, packet.gid), TTL_SECONDS, payload)


async def cache_winprob(redis: Redis, msg: WinProbMsg) -> None:
    """Store the win probability message for quick reads."""

    payload = json.dumps(msg.model_dump(mode="json"))
    await redis.setex(_key(WIN_PROB_KEY, msg.gid), TTL_SECONDS, payload)


async def publish_update(redis: Redis, msg: WinProbMsg) -> None:
    """Publish the latest win probability to interested subscribers."""

    await redis.publish(PUBSUB_CHANNEL, json.dumps(msg.model_dump(mode="json")))


async def append_stream(redis: Redis, packet: LivePacket) -> str:
    """Append the raw packet to a Redis stream for auditing purposes."""

    fields: Iterable[Tuple[str, Any]] = (
        ("gid", packet.gid),
        ("ts", packet.ts),
        ("y_pred", packet.y_pred),
        ("model_version", packet.model_version),
    )
    entries = {k: json.dumps(v) if isinstance(v, (dict, list)) else v for k, v in fields}
    return await redis.xadd(STREAM_KEY, entries)
