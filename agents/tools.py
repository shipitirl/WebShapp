"""Collection of Python-callable tools used by orchestration agents."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import duckdb
import polars as pl

from backend.deps import DUCKDB_PATH, get_duckdb


def load_parquet(partition_glob: str) -> Dict[str, Any]:
    """Return basic stats for a parquet glob."""

    lf = pl.scan_parquet(partition_glob)
    return {"columns": lf.columns, "rows_estimate": lf.describe().collect().shape[0]}


def refresh_duckdb() -> None:
    conn = get_duckdb()
    conn.execute("DETACH IF EXISTS parquet_db")
    conn.execute("PRAGMA optimize;")


def publish_winprob(gid: str, payload: Dict[str, Any]) -> None:
    Path("logs").mkdir(exist_ok=True)
    path = Path("logs") / "winprob.log"
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"gid": gid, **payload}) + "\n")


def compute_drift(season: int, week: int) -> Dict[str, Any]:
    conn = duckdb.connect(str(DUCKDB_PATH))
    result = conn.execute(
        "SELECT COUNT(*) FROM parquet_scan('data/nfl_predictions/season=*/week=*/*.parquet')"
    ).fetchone()
    count = result[0] if result else 0
    trigger = count % 5 == 0 and count > 0
    return {
        "season": season,
        "week": week,
        "trigger": trigger,
        "model_version": "v0",
        "reason": "count multiple of 5" if trigger else "stable",
    }


def trigger_retrain(model_version: str, reason: str) -> None:
    Path("logs").mkdir(exist_ok=True)
    path = Path("logs") / "retrain_requests.log"
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"model_version": model_version, "reason": reason}) + "\n")
