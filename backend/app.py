"""FastAPI application exposing REST endpoints for live analytics."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from . import ws
from .deps import get_duckdb
from .routers import games, shap, winprob
from .workers import scheduler

logger = logging.getLogger(__name__)

app = FastAPI(title="SHAP-Aware Live Win % Engine", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(games.router, prefix="/api/game", tags=["game"])
app.include_router(shap.router, prefix="/api/shap", tags=["shap"])
app.include_router(winprob.router, prefix="/api/winprob", tags=["winprob"])


@app.on_event("startup")
async def _startup() -> None:
    logger.info("Starting SHAP Live Engine application")
    scheduler.start()
    loop = asyncio.get_event_loop()
    loop.run_in_executor(None, lambda: get_duckdb())


@app.on_event("shutdown")
async def _shutdown() -> None:
    logger.info("Stopping background scheduler")
    await scheduler.stop()


@app.websocket("/ws/live")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await ws.manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        logger.info("Websocket disconnect")
    finally:
        await ws.manager.disconnect(websocket)
