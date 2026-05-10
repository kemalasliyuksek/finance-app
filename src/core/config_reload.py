"""Dinamik config reload helper'ları.

`apply_config_to_settings` — settings singleton'ını DB'den gelen
değerlerle senkronlar, Pydantic validator'larını çalıştırır.

`config_listener` — Redis `config:updated` kanalını dinler ve
diğer container'lardaki (trading-bot, trading-telegram) settings'i
yerel olarak günceller.
"""

from __future__ import annotations

import json
from typing import Any

from pydantic import ValidationError

from src.config import Settings, settings
from src.core.events import get_redis
from src.core.logging import get_logger

logger = get_logger("config_reload")

CONFIG_UPDATED_CHANNEL = "config:updated"


def validate_config_updates(values: dict[str, Any]) -> Settings:
    """Kısmi güncellemeyi settings'e dokunmadan validate et.

    Mevcut singleton + override birleşimini içeren yeni bir Settings
    objesi oluşturur. Validator'lar başarısız olursa ValidationError
    fırlatır; başarılıysa validated objeyi döndürür (caller isterse
    `apply_config_to_settings` ile uygulamayabilir).
    """
    merged = {**settings.model_dump(), **values}
    return Settings(**merged)


async def apply_config_to_settings(values: dict[str, Any]) -> None:
    """settings singleton'ının alanlarını DB değerleriyle senkronla.

    Validate et, başarılıysa setattr ile uygula. Caller validation'ı
    kendisi çağırdıysa bu yine idempotent — ikinci validate'in maliyeti
    ihmal edilebilir.

    Raises:
        ValidationError: Geçersiz değer kombinasyonu.
    """
    if not values:
        return

    validated = validate_config_updates(values)

    for key in values:
        if hasattr(settings, key):
            setattr(settings, key, getattr(validated, key))

    logger.info("config_applied", keys=sorted(values.keys()))


async def config_listener() -> None:
    """Redis config:updated kanalını dinleyen background task.

    Her container (trading-bot + trading-telegram) kendi process'inde
    bu listener'ı başlatır. Dashboard'dan gelen PATCH /api/v1/config
    sonrasında publish edilen mesaj tüm dinleyicilere ulaşır ve yerel
    settings güncellenir.
    """
    r = await get_redis()
    pubsub = r.pubsub()
    await pubsub.subscribe(CONFIG_UPDATED_CHANNEL)
    logger.info("config_listener_started", channel=CONFIG_UPDATED_CHANNEL)

    try:
        async for message in pubsub.listen():
            if message.get("type") != "message":
                continue
            try:
                raw = message.get("data")
                if isinstance(raw, bytes):
                    raw = raw.decode()
                data = json.loads(raw) if isinstance(raw, str) else raw
                changes = data.get("changes", {}) if isinstance(data, dict) else {}
                if changes:
                    await apply_config_to_settings(changes)
            except ValidationError:
                logger.exception("config_reload_validation_failed")
            except Exception:
                logger.exception("config_reload_failed")
    finally:
        try:
            await pubsub.unsubscribe(CONFIG_UPDATED_CHANNEL)
            await pubsub.close()
        except Exception:
            pass
        logger.info("config_listener_stopped")
