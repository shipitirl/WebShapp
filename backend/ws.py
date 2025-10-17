"""Websocket management for broadcasting live updates."""
from __future__ import annotations

import asyncio
import json
from typing import Dict, Set

from fastapi import WebSocket


class ConnectionManager:
    """Book-keeping for websocket clients."""

    def __init__(self) -> None:
        self._connections: Set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections.add(websocket)

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._connections.discard(websocket)

    async def broadcast(self, message: Dict[str, object]) -> None:
        payload = json.dumps(message)
        async with self._lock:
            recipients = list(self._connections)
        await asyncio.gather(
            *[self._safe_send(ws, payload) for ws in recipients], return_exceptions=True
        )

    async def _safe_send(self, websocket: WebSocket, payload: str) -> None:
        try:
            await websocket.send_text(payload)
        except Exception:
            await self.disconnect(websocket)


manager = ConnectionManager()
