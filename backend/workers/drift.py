"""Periodically compute feature drift using historical SHAP vectors."""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import polars as pl

from backend.deps import get_duckdb
from backend.queries import PARQUET_GLOB
from agents.tools import compute_drift, trigger_retrain

logger = logging.getLogger(__name__)


async def drift_job() -> None:
    logger.info("Running drift detection job")
    lf = pl.scan_parquet(PARQUET_GLOB)
    if lf.schema is None:
        logger.info("No data for drift detection yet")
        return
    report = compute_drift(datetime.now(timezone.utc).year, 0)
    if report.get("trigger", False):
        trigger_retrain(report["model_version"], report["reason"])
    Path("reports").mkdir(exist_ok=True)
    path = Path("reports") / f"drift_{datetime.now().date()}.json"
    path.write_text(json.dumps(report, indent=2))


async def main() -> None:
    while True:
        await drift_job()
        await asyncio.sleep(300)


if __name__ == "__main__":
    asyncio.run(main())
