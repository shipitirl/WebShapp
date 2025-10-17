from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Deque, Optional

from ..config import settings
from ..models import (
    GameState,
    PauseRequest,
    PlayEvent,
    ShapSnapshot,
    TimelinePoint,
    WebsocketPayload,
)
from .shap_adapter import ShapAdapter


class QueueDepthExceeded(RuntimeError):
    pass


@dataclass(eq=False)
class FakeWebSocket:
    messages: asyncio.Queue[dict]

    async def send_json(self, payload: dict) -> None:
        await self.messages.put(payload)

    def __hash__(self) -> int:  # pragma: no cover - trivial
        return id(self)


class GameSession:
    def __init__(self, game_id: str, home_team: str, away_team: str, plays: list[PlayEvent]):
        self.game_id = game_id
        self.home_team = home_team
        self.away_team = away_team
        self.plays = plays
        self.state = GameState(
            game_id=game_id,
            home_team=home_team,
            away_team=away_team,
            started_at=datetime.now(UTC),
            total_plays=len(plays),
        )
        self.timeline: Deque[TimelinePoint] = deque(maxlen=512)
        self._adapter = ShapAdapter()
        self._index = 0
        self._paused = asyncio.Event()
        self._paused.set()
        self._replay_task: Optional[asyncio.Task] = None
        self._latencies: list[float] = []
        self._prediction_latencies: list[float] = []
        self._connections: set[FakeWebSocket] = set()

    @property
    def latencies(self) -> list[float]:
        return list(self._latencies)

    @property
    def prediction_latencies(self) -> list[float]:
        return list(self._prediction_latencies)

    async def register(self) -> FakeWebSocket:
        connection = FakeWebSocket(asyncio.Queue())
        self._connections.add(connection)
        await connection.send_json(WebsocketPayload("game_state", self.state.to_dict()).to_dict())
        return connection

    def unregister(self, connection: FakeWebSocket) -> None:
        self._connections.discard(connection)

    async def broadcast(self, payload_type: str, data: dict) -> None:
        payload = WebsocketPayload(payload_type, data).to_dict()
        await asyncio.gather(*(connection.send_json(payload) for connection in list(self._connections)))

    async def start_replay(self, pace_multiplier: float) -> asyncio.Task:
        if self._replay_task and not self._replay_task.done():
            return self._replay_task
        self._replay_task = asyncio.create_task(self._run_replay(pace_multiplier))
        return self._replay_task

    async def set_paused(self, request: PauseRequest) -> None:
        if request.paused:
            self._paused.clear()
        else:
            self._paused.set()

    async def _run_replay(self, pace_multiplier: float) -> None:
        loop = asyncio.get_event_loop()
        while self._index < len(self.plays):
            await self._paused.wait()
            play = self.plays[self._index]
            self._index += 1

            pred_start = loop.time()
            await asyncio.sleep(settings.prediction_delay_seconds / max(pace_multiplier, 0.1))
            self._prediction_latencies.append((loop.time() - pred_start) * 1000.0)
            await self.broadcast("prediction", {"play_id": play.play_id, "prediction": play.prediction})

            shap_snapshot: ShapSnapshot = await loop.run_in_executor(None, self._adapter.compute, play)
            self._latencies.append(shap_snapshot.latency_ms)
            await self.broadcast("shap", shap_snapshot.to_dict())

            timeline_point = TimelinePoint(
                play_id=play.play_id,
                shap_sum=sum(value.value for value in shap_snapshot.top_features),
                timestamp=datetime.now(UTC),
            )
            self.timeline.append(timeline_point)
            await self.broadcast("timeline", timeline_point.to_dict())
            await asyncio.sleep(settings.replay_loop_sleep)

    def latest_timeline(self) -> list[TimelinePoint]:
        return list(self.timeline)


class GameEngine:
    def __init__(self) -> None:
        self._sessions: dict[str, GameSession] = {}
        self._idempotency_keys: set[str] = set()

    def ingest(self, game_id: str, home_team: str, away_team: str, plays: list[PlayEvent], *, idempotency_key: str) -> GameSession:
        if idempotency_key in self._idempotency_keys and game_id in self._sessions:
            return self._sessions[game_id]
        if len(plays) > settings.max_queue_depth:
            raise QueueDepthExceeded("Too many plays queued")
        session = GameSession(game_id, home_team, away_team, plays)
        self._sessions[game_id] = session
        self._idempotency_keys.add(idempotency_key)
        return session

    def get(self, game_id: str) -> GameSession:
        if game_id not in self._sessions:
            raise KeyError(f"Unknown game {game_id}")
        return self._sessions[game_id]

    def search(self, query: str, *, limit: int = 10) -> list[PlayEvent]:
        results: list[PlayEvent] = []
        lower_query = query.lower()
        for session in self._sessions.values():
            for play in session.plays:
                haystack = " ".join(
                    str(getattr(play, field))
                    for field in settings.default_search_fields
                    if hasattr(play, field)
                )
                if lower_query in haystack.lower():
                    results.append(play)
                    if len(results) >= limit:
                        return results
        return results

    def metrics(self, game_id: str) -> dict[str, float]:
        session = self.get(game_id)
        if session.latencies:
            sorted_latencies = sorted(session.latencies)
            index = max(int(0.95 * len(sorted_latencies)) - 1, 0)
            p95 = sorted_latencies[index]
        else:
            p95 = 0.0
        if session.prediction_latencies:
            sorted_pred = sorted(session.prediction_latencies)
            pred_index = max(int(0.95 * len(sorted_pred)) - 1, 0)
            pred_p95 = sorted_pred[pred_index]
        else:
            pred_p95 = 0.0
        queue_depth = max(0, len(session.plays) - session._index)
        return {
            "p95_shap_latency_ms": p95,
            "prediction_latency_p95_ms": pred_p95,
            "queue_depth": queue_depth,
            "max_queue_depth": settings.max_queue_depth,
        }


def create_engine() -> GameEngine:
    return GameEngine()
