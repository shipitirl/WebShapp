from __future__ import annotations

import asyncio
from pathlib import Path

from app.models import InjectionRequest, PauseRequest, StartReplayRequest
from app.service_layer import get_metrics, ingest_game, pause_game, search, start_replay
from app.services.game_engine import GameEngine


def test_full_stack_flow() -> None:
    asyncio.run(run_full_stack_flow())


async def run_full_stack_flow() -> None:
    engine = GameEngine()
    fixture_path = Path("fixtures/sample_game.parquet").resolve()

    ingest_request = InjectionRequest(
        parquet_path=str(fixture_path),
        home_team="Home Heroes",
        away_team="Away Warriors",
        idempotency_key="abc123",
    )

    ingest_result = ingest_game(engine, "TESTGAME", ingest_request)
    assert ingest_result["total_plays"] >= 10

    # idempotent re-ingest
    ingest_result_repeat = ingest_game(engine, "TESTGAME", ingest_request)
    assert ingest_result_repeat == ingest_result

    start_request = StartReplayRequest(pace_multiplier=5)
    start_info = start_replay(engine, "TESTGAME", start_request)
    assert start_info["status"] == "started"

    session = engine.get("TESTGAME")
    websocket = await session.register()

    async def consume_messages():
        received = []
        while len(received) < 30:
            message = await asyncio.wait_for(websocket.messages.get(), timeout=5)
            received.append(message)
            if len([m for m in received if m["type"] == "timeline"]) >= 10:
                break
        return received

    consumer_task = asyncio.create_task(consume_messages())

    # start the replay loop
    replay_task = await start_info["task"]
    await replay_task

    messages = await consumer_task

    assert messages[0]["type"] == "game_state"
    stream_types = [msg["type"] for msg in messages if msg["type"] in {"prediction", "shap"}]
    assert stream_types[:2] == ["prediction", "shap"]
    for idx in range(0, min(20, len(stream_types)), 2):
        if idx + 1 >= len(stream_types):
            break
        assert stream_types[idx] == "prediction"
        assert stream_types[idx + 1] == "shap"

    timeline_payloads = [msg["data"] for msg in messages if msg["type"] == "timeline"]
    assert timeline_payloads
    assert timeline_payloads[-1]["shap_sum"] != 0

    metrics = get_metrics(engine, "TESTGAME")
    assert metrics["p95_shap_latency_ms"] < 1500
    assert metrics["queue_depth"] < metrics["max_queue_depth"]

    search_results = search(engine, "Play number 1")
    assert search_results

    pause_result = pause_game(engine, "TESTGAME", PauseRequest(paused=True))
    resume_result = pause_game(engine, "TESTGAME", PauseRequest(paused=False))
    await pause_result["task"]
    await resume_result["task"]
    assert pause_result["paused"] is True
    assert resume_result["paused"] is False
