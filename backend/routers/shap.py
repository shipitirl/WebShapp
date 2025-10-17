"""SHAP aggregation endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Query

from ..deps import DuckDBDep
from ..queries import fetch_top_shap
from ..schemas import TopShapResponse

router = APIRouter()


@router.get("/{gid}/topk", response_model=TopShapResponse)
def top_k_shap(gid: str, k: int = Query(15, ge=1, le=50), conn=DuckDBDep) -> TopShapResponse:
    items = fetch_top_shap(conn, gid, limit=k)
    return TopShapResponse(gid=gid, items=items)
