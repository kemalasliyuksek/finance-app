"""WebSocket bağlantı yöneticisi - Redis pub/sub → WebSocket bridge."""

from __future__ import annotations

import asyncio
import json

from fastapi import WebSocket

from src.core.events import get_redis
from src.core.logging import get_logger

logger = get_logger("ws_manager")


class ConnectionManager:
    """WebSocket bağlantılarını yönetir ve Redis pub/sub'ı bridge eder."""

    def __init__(self) -> None:
        self.active_connections: set[WebSocket] = set()
        self._listener_task: asyncio.Task | None = None

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info("ws_client_connected", total=len(self.active_connections))

    def disconnect(self, websocket: WebSocket) -> None:
        self.active_connections.discard(websocket)
        logger.info("ws_client_disconnected", total=len(self.active_connections))

    async def broadcast(self, message: dict) -> None:
        """Tüm bağlı istemcilere mesaj gönder."""
        if not self.active_connections:
            return
        payload = json.dumps(message, default=str)
        dead: list[WebSocket] = []
        for ws in self.active_connections:
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.active_connections.discard(ws)

    async def start_redis_listener(self) -> None:
        """Redis pub/sub kanallarını dinle ve WebSocket'e bridge et."""
        r = await get_redis()
        pubsub = r.pubsub()

        await pubsub.psubscribe(
            "candle:closed:*",
            "signal:new",
            "signal:approved",
            "order:filled",
            "order:executed",
            "sentiment:*",
            "config:pairs_updated",
            "config:updated",
            "screener:results",
        )

        logger.info("redis_ws_bridge_started")

        try:
            while True:
                message = await pubsub.get_message(
                    ignore_subscribe_messages=True, timeout=1.0,
                )
                if message and message["type"] == "pmessage":
                    channel = message["channel"]
                    try:
                        data = json.loads(message["data"])
                    except (json.JSONDecodeError, TypeError):
                        data = {"raw": message["data"]}

                    event_type = self._channel_to_event_type(channel)
                    await self.broadcast({
                        "type": event_type,
                        "channel": channel,
                        "data": data,
                    })
                else:
                    await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            await pubsub.punsubscribe()
            await pubsub.close()
            logger.info("redis_ws_bridge_stopped")

    def _channel_to_event_type(self, channel: str) -> str:
        if channel.startswith("candle:closed:"):
            return "candle"
        if channel in ("signal:new", "signal:approved"):
            return "signal"
        if channel in ("order:filled", "order:executed"):
            return "order"
        if channel.startswith("sentiment:"):
            return "sentiment"
        if channel in ("config:pairs_updated", "config:updated"):
            return "config"
        if channel == "screener:results":
            return "screener"
        return "unknown"

    async def start(self) -> None:
        """Redis listener'ı background task olarak başlat."""
        self._listener_task = asyncio.create_task(
            self.start_redis_listener(), name="ws_redis_bridge",
        )

    async def stop(self) -> None:
        """Redis listener'ı durdur."""
        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass


ws_manager = ConnectionManager()
