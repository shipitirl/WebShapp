from __future__ import annotations

import asyncio
from dataclasses import asdict
from pathlib import Path

from .models import InjectionRequest, PauseRequest, StartReplayRequest
from .service_layer import get_metrics, ingest_game, pause_game, search, start_replay
from .services.game_engine import GameEngine


async def run_demo(parquet_path: Path) -> None:
    engine = GameEngine()
    request = InjectionRequest(
        parquet_path=str(parquet_path),
        home_team="Home Heroes",
        away_team="Away Warriors",
        idempotency_key="demo",
    )
    ingest_game(engine, "DEMO", request)
    session = engine.get("DEMO")
    websocket = await session.register()

    start_info = start_replay(engine, "DEMO", StartReplayRequest(pace_multiplier=5))
    replay_task = await start_info["task"]
    consumer = asyncio.create_task(_log_messages(websocket))
    await replay_task
    await consumer
    metrics = get_metrics(engine, "DEMO")
    print("Metrics:", metrics)
    print("Search for 'Play number 1':", [asdict(result) for result in search(engine, "Play number 1")])
    pause_result = pause_game(engine, "DEMO", PauseRequest(paused=True))
    await pause_result["task"]
    resume_result = pause_game(engine, "DEMO", PauseRequest(paused=False))
    await resume_result["task"]


async def _log_messages(websocket) -> None:
    count = 0
    while count < 15:
        message = await websocket.messages.get()
        print(message)
        count += 1


if __name__ == "__main__":
    fixture = Path("fixtures/sample_game.parquet")
    asyncio.run(run_demo(fixture))
