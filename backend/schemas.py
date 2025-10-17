"""Pydantic models shared across the backend services."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ShapItem(BaseModel):
    """SHAP contribution for a single feature."""

    model_config = ConfigDict(extra="ignore")

    f: str = Field(..., description="Feature name")
    s: float = Field(..., description="SHAP contribution value")


class GameState(BaseModel):
    """Subset of the live game state sent from the upstream model."""

    q: int = Field(..., description="Quarter number")
    time_left: int = Field(..., description="Remaining time in seconds")
    down: int = Field(..., ge=0, le=4)
    dist: int = Field(..., description="Distance to first down")
    yardline: int = Field(..., ge=0, le=100)
    to_a: int = Field(..., ge=0, le=3)
    to_b: int = Field(..., ge=0, le=3)
    score_a: int
    score_b: int


class LivePacket(BaseModel):
    """Raw payload emitted by the upstream inference service."""

    gid: str
    ts: int
    y_pred: float
    state: Dict[str, Any]
    shap: List[ShapItem]
    model_version: str
    play_id: Optional[str] = None


class WinProbMsg(BaseModel):
    """Payload published to Redis/websocket clients after smoothing."""

    gid: str
    ts: int
    p_win: float
    explain: Dict[str, Any]


class HistoryPoint(BaseModel):
    """Time-series point returned from the history endpoint."""

    ts: int
    p_win: float


class HistoryResponse(BaseModel):
    """History response envelope."""

    gid: str
    points: List[HistoryPoint]


class TopShapItem(BaseModel):
    """Aggregated SHAP contribution used in analytics views."""

    feature: str
    impact: float


class TopShapResponse(BaseModel):
    """Collection of aggregated SHAP items."""

    gid: str
    items: List[TopShapItem]
