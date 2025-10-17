from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Iterable

from ..models import PlayEvent

try:  # pragma: no cover - optional dependency
    import pandas as pd  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    pd = None


class ParquetLoaderError(RuntimeError):
    pass


REQUIRED_COLUMNS = {
    "play_id",
    "description",
    "team",
    "quarter",
    "time_remaining",
    "prediction",
    "timestamp",
}


def _row_to_play(row: dict) -> PlayEvent:
    features = {
        key: float(value)
        for key, value in row.items()
        if key not in REQUIRED_COLUMNS
    }
    return PlayEvent(
        play_id=str(row["play_id"]),
        description=str(row["description"]),
        team=str(row["team"]),
        quarter=int(row["quarter"]),
        time_remaining=float(row["time_remaining"]),
        features=features,
        prediction=float(row["prediction"]),
        timestamp=datetime.fromisoformat(str(row["timestamp"])),
    )


def load_parquet(path: str | Path) -> list[PlayEvent]:
    parquet_path = Path(path)
    if not parquet_path.exists():
        raise ParquetLoaderError(f"Parquet file {path} does not exist")

    if pd is not None:
        df = pd.read_parquet(parquet_path)
        missing = REQUIRED_COLUMNS - set(df.columns)
        if missing:
            raise ParquetLoaderError(f"Parquet file missing required columns: {sorted(missing)}")
        plays: Iterable[PlayEvent] = (
            _row_to_play(row.to_dict())  # type: ignore[call-arg]
            for _, row in df.iterrows()
        )
        return list(plays)

    # Fallback: treat the file as json lines encoded inside the parquet placeholder
    try:
        rows = json.loads(parquet_path.read_text())
    except json.JSONDecodeError as exc:  # pragma: no cover - incorrect format
        raise ParquetLoaderError("File is neither real parquet nor JSON fallback") from exc

    if not isinstance(rows, list):
        raise ParquetLoaderError("Fallback parquet format expects a list of rows")

    plays = []
    for row in rows:
        missing = REQUIRED_COLUMNS - row.keys()
        if missing:
            raise ParquetLoaderError(f"Row missing required columns: {sorted(missing)}")
        plays.append(_row_to_play(row))
    return plays


def ensure_sorted_by_timestamp(plays: list[PlayEvent]) -> list[PlayEvent]:
    return sorted(plays, key=lambda play: play.timestamp)
