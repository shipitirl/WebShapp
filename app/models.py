from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Literal


@dataclass(slots=True)
class PlayEvent:
    play_id: str
    description: str
    team: str
    quarter: int
    time_remaining: float
    features: dict[str, float]
    prediction: float
    timestamp: datetime

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["timestamp"] = self.timestamp.isoformat()
        return payload


@dataclass(slots=True)
class GameState:
    game_id: str
    home_team: str
    away_team: str
    started_at: datetime
    total_plays: int

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["started_at"] = self.started_at.isoformat()
        return payload


@dataclass(slots=True)
class ShapValue:
    feature: str
    value: float


@dataclass(slots=True)
class ShapSnapshot:
    play_id: str
    shap_values: list[ShapValue]
    top_features: list[ShapValue]
    generated_at: datetime
    latency_ms: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "play_id": self.play_id,
            "shap_values": [asdict(value) for value in self.shap_values],
            "top_features": [asdict(value) for value in self.top_features],
            "generated_at": self.generated_at.isoformat(),
            "latency_ms": self.latency_ms,
        }


@dataclass(slots=True)
class TimelinePoint:
    play_id: str
    shap_sum: float
    timestamp: datetime

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["timestamp"] = self.timestamp.isoformat()
        return payload


@dataclass(slots=True)
class WebsocketPayload:
    type: Literal["game_state", "prediction", "shap", "timeline"]
    data: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {"type": self.type, "data": self.data}


@dataclass(slots=True)
class SearchResult:
    play_id: str
    description: str
    team: str
    quarter: int
    time_remaining: float
    prediction: float


@dataclass(slots=True)
class InjectionRequest:
    parquet_path: str
    home_team: str
    away_team: str
    idempotency_key: str


@dataclass(slots=True)
class StartReplayRequest:
    pace_multiplier: float = 1.0


@dataclass(slots=True)
class PauseRequest:
    paused: bool
