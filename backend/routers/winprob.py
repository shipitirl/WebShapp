"""Endpoints to expose win probability data."""
from __future__ import annotations

from fastapi import APIRouter

from ..deps import RedisDep
from ..schemas import WinProbMsg

router = APIRouter()


@router.get("/{gid}", response_model=WinProbMsg)
async def get_winprob(gid: str, redis=RedisDep) -> WinProbMsg:
    payload = await redis.get(f"game:{gid}:winprob")
    if not payload:
        raise RuntimeError("Win probability not available")
    return WinProbMsg.model_validate_json(payload)
