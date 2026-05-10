"""WebSocket endpoint - gerçek zamanlı veri akışı."""

from __future__ import annotations

import jwt
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from src.api.auth import verify_token
from src.api.ws_manager import ws_manager

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str | None = None) -> None:
    """WebSocket bağlantısı - JWT ile kimlik doğrulama."""
    if not token:
        await websocket.close(code=4001, reason="Token gerekli")
        return

    try:
        verify_token(token, expected_type="access")
    except jwt.PyJWTError:
        await websocket.close(code=4001, reason="Geçersiz token")
        return

    await ws_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
