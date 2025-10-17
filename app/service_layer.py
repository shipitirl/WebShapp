from __future__ import annotations

import asyncio

from .models import (
    InjectionRequest,
    PauseRequest,
    SearchResult,
    StartReplayRequest,
)
from .services.game_engine import GameEngine
from .services.parquet_loader import ensure_sorted_by_timestamp, load_parquet


class ServiceError(RuntimeError):
    pass


class NotFound(ServiceError):
    pass


def ingest_game(engine: GameEngine, game_id: str, request: InjectionRequest) -> dict:
    plays = ensure_sorted_by_timestamp(load_parquet(request.parquet_path))
    session = engine.ingest(
        game_id,
        request.home_team,
        request.away_team,
        plays,
        idempotency_key=request.idempotency_key,
    )
    return {"game_id": session.game_id, "total_plays": len(session.plays)}


def start_replay(engine: GameEngine, game_id: str, request: StartReplayRequest) -> dict:
    try:
        session = engine.get(game_id)
    except KeyError as exc:
        raise NotFound(str(exc)) from exc
    task = asyncio.create_task(session.start_replay(request.pace_multiplier))
    return {"status": "started", "pace_multiplier": request.pace_multiplier, "task": task}


def pause_game(engine: GameEngine, game_id: str, request: PauseRequest) -> dict:
    try:
        session = engine.get(game_id)
    except KeyError as exc:
        raise NotFound(str(exc)) from exc
    task = asyncio.create_task(session.set_paused(request))
    return {"task": task, "paused": request.paused}


def get_metrics(engine: GameEngine, game_id: str) -> dict:
    try:
        return engine.metrics(game_id)
    except KeyError as exc:
        raise NotFound(str(exc)) from exc


def search(engine: GameEngine, query: str, limit: int = 10) -> list[SearchResult]:
    results = engine.search(query, limit=limit)
    return [
        SearchResult(
            play_id=play.play_id,
            description=play.description,
            team=play.team,
            quarter=play.quarter,
            time_remaining=play.time_remaining,
            prediction=play.prediction,
        )
        for play in results
    ]
