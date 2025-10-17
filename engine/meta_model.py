"""SHAP-aware stage-2 model for win probability smoothing."""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, Iterable, List

from backend.schemas import LivePacket, WinProbMsg

from .shap_utils import bucketize_shap


@dataclass
class MetaModelConfig:
    """Configuration for the meta-model."""

    alpha: float = 0.15
    beta: Dict[str, float] = field(default_factory=lambda: {
        "bias": 0.0,
        "y_pred": 1.0,
        "QB": 0.2,
        "WR": 0.1,
        "OL": 0.05,
        "DEF": -0.1,
        "SITUATION": 0.4,
        "OTHER": 0.05,
    })


class MetaModel:
    """Low-latency logistic model with exponential smoothing."""

    def __init__(self, config: MetaModelConfig | None = None) -> None:
        self.config = config or MetaModelConfig()
        self._state: Dict[str, float] = {}

    def update(self, packet: LivePacket) -> WinProbMsg:
        buckets = bucketize_shap(packet.shap)
        logit = self.config.beta["bias"] + self.config.beta["y_pred"] * packet.y_pred
        for bucket, value in buckets.items():
            weight = self.config.beta.get(bucket, 0.0)
            logit += weight * value
        p_raw = 1 / (1 + math.exp(-logit))
        p_prev = self._state.get(packet.gid, p_raw)
        p_smooth = (1 - self.config.alpha) * p_prev + self.config.alpha * p_raw
        self._state[packet.gid] = p_smooth
        return WinProbMsg(
            gid=packet.gid,
            ts=packet.ts,
            p_win=p_smooth,
            explain={"raw": p_raw, "buckets": buckets, "alpha": self.config.alpha},
        )


meta_model = MetaModel()
