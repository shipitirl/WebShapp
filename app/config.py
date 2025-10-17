from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class Settings:
    shap_delay_seconds: float = 0.05
    prediction_delay_seconds: float = 0.02
    shap_top_k: int = 5
    max_queue_depth: int = 256
    replay_loop_sleep: float = 0.01
    default_search_fields: tuple[str, ...] = ("play_id", "description", "team")


settings = Settings()
