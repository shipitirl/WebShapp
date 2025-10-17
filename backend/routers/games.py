"""Endpoints related to live game snapshots and history."""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from ..cache import WIN_PROB_KEY, _key
from ..deps import DuckDBDep, RedisDep
from ..schemas import HistoryPoint, HistoryResponse, WinProbMsg

router = APIRouter()


@router.get("/{gid}/snapshot", response_model=WinProbMsg)
async def get_snapshot(gid: str, redis=RedisDep) -> WinProbMsg:
    payload = await redis.get(_key(WIN_PROB_KEY, gid))
    if not payload:
        raise HTTPException(status_code=404, detail="Game not found")
    return WinProbMsg.model_validate_json(payload)


@router.get("/{gid}/history", response_model=HistoryResponse)
async def get_history(
    gid: str,
    since: Optional[int] = Query(None, description="Unix timestamp (ms) lower bound"),
    conn=DuckDBDep,
) -> HistoryResponse:
    conn.execute(
        """
        SELECT ts, p_win FROM shap_live
        WHERE game_id = ? AND (? IS NULL OR ts >= ?)
        ORDER BY ts ASC
        """,
        [gid, since, since],
    )
    rows = conn.fetchall()
    points = [HistoryPoint(ts=row[0], p_win=row[1]) for row in rows]
    return HistoryResponse(gid=gid, points=points)
