"""Helper utilities for working with SHAP vectors."""
from __future__ import annotations

from collections import defaultdict
from typing import Dict, Iterable, List

from backend.schemas import ShapItem

BUCKET_MAP = {
    "QB": {"QB_pressure_rate", "QB_scramble_rate"},
    "WR": {"WR_sep", "WR_yards_after_catch"},
    "OL": {"OL_win_rate"},
    "DEF": {"DEF_pressure", "DEF_pass_rush"},
    "SITUATION": {"score_diff", "time_left"},
}


def bucketize_shap(shap_values: Iterable[ShapItem]) -> Dict[str, float]:
    """Aggregate SHAP contributions into pre-defined feature buckets."""

    totals: Dict[str, float] = defaultdict(float)
    for item in shap_values:
        assigned = False
        for bucket, features in BUCKET_MAP.items():
            if item.f in features:
                totals[bucket] += item.s
                assigned = True
                break
        if not assigned:
            totals["OTHER"] += item.s
    return dict(totals)


def flatten_shap(shap_values: Iterable[ShapItem]) -> List[float]:
    """Return the raw SHAP vector."""

    return [item.s for item in shap_values]
