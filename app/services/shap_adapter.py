from __future__ import annotations

import random
import time
from collections.abc import Iterable
from datetime import UTC, datetime

from ..config import settings
from ..models import PlayEvent, ShapSnapshot, ShapValue


class ShapAdapter:
    def __init__(self) -> None:
        self._rng = random.Random(42)

    def compute(self, play: PlayEvent) -> ShapSnapshot:
        start = time.perf_counter()
        time.sleep(settings.shap_delay_seconds)
        contributions = []
        for feature, value in sorted(play.features.items()):
            weight = self._rng.uniform(0.5, 1.5)
            contributions.append(
                ShapValue(feature=feature, value=weight * value - 0.1 * play.prediction)
            )
        contributions.sort(key=lambda value: abs(value.value), reverse=True)
        top_k = contributions[: settings.shap_top_k]
        latency_ms = (time.perf_counter() - start) * 1000.0
        return ShapSnapshot(
            play_id=play.play_id,
            shap_values=contributions,
            top_features=top_k,
            generated_at=datetime.now(UTC),
            latency_ms=latency_ms,
        )


def compute_shap_batch(plays: Iterable[PlayEvent]) -> list[ShapSnapshot]:
    adapter = ShapAdapter()
    return [adapter.compute(play) for play in plays]
