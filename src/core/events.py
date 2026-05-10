"""Redis pub/sub event bus - modüller arası iletişim."""

from __future__ import annotations

import json
from typing import Any

import redis.asyncio as aioredis

from src.config import settings
from src.core.logging import get_logger

logger = get_logger("events")

_redis: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    """Singleton Redis bağlantısı döndür."""
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(
            settings.redis_url,
            decode_responses=True,
            max_connections=20,
        )
    return _redis


async def publish(channel: str, data: dict[str, Any]) -> None:
    """Redis kanalına mesaj yayınla."""
    r = await get_redis()
    payload = json.dumps(data, default=str)
    await r.publish(channel, payload)
    logger.debug("event_published", channel=channel)


async def set_cache(key: str, value: Any, ttl_seconds: int = 300) -> None:
    """Redis'e cache değeri yaz."""
    r = await get_redis()
    payload = json.dumps(value, default=str)
    await r.set(key, payload, ex=ttl_seconds)


async def get_cache(key: str) -> Any | None:
    """Redis'ten cache değeri oku."""
    r = await get_redis()
    data = await r.get(key)
    if data is None:
        return None
    return json.loads(data)


async def close_redis() -> None:
    """Redis bağlantısını kapat."""
    global _redis
    if _redis is not None:
        await _redis.close()
        _redis = None
