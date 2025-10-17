"""Query layer for DuckDB and Polars analytics."""
from __future__ import annotations

from pathlib import Path
from typing import Iterable, List

import duckdb
import polars as pl

from .schemas import TopShapItem

DATA_ROOT = Path("data/nfl_predictions")
PARQUET_GLOB = str(DATA_ROOT / "season=*" / "week=*" / "*.parquet")


def ensure_view(conn: duckdb.DuckDBPyConnection) -> None:
    """Create the canonical DuckDB view if it does not yet exist."""

    conn.execute(
        """
        CREATE OR REPLACE VIEW shap_live AS
        SELECT * FROM parquet_scan(?)
        """,
        [PARQUET_GLOB],
    )


def fetch_top_shap(conn: duckdb.DuckDBPyConnection, gid: str, limit: int = 15) -> List[TopShapItem]:
    """Return the top SHAP contributors for the specified game."""

    ensure_view(conn)
    query = (
        "SELECT shap.feature AS feature, AVG(shap.value) AS impact\n"
        "FROM shap_live\n"
        "WHERE game_id = ?\n"
        "CROSS JOIN UNNEST(shap) AS shap(feature, value)\n"
        "GROUP BY feature\n"
        "ORDER BY impact DESC\n"
        "LIMIT ?"
    )
    result = conn.execute(query, [gid, limit]).fetchall()
    return [TopShapItem(feature=row[0], impact=row[1]) for row in result]


def fetch_top_shap_polars(gid: str, limit: int = 15) -> List[TopShapItem]:
    """Perform the same aggregation using Polars for heavy workloads."""

    lf = pl.scan_parquet(PARQUET_GLOB)
    top = (
        lf.filter(pl.col("game_id") == gid)
        .select(pl.col("shap"))
        .explode("shap")
        .select(
            pl.col("shap").struct.field("feature").alias("feature"),
            pl.col("shap").struct.field("value").alias("impact"),
        )
        .group_by("feature")
        .agg(pl.col("impact").mean().alias("impact"))
        .sort("impact", descending=True)
        .head(limit)
    )
    return [TopShapItem(feature=row["feature"], impact=row["impact"]) for row in top.collect(streaming=True).to_dicts()]
