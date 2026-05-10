"""Sentiment motoru - periyodik haber analizi ve skor guncelleme."""

from __future__ import annotations

import asyncio

from src.config import settings
from src.core.logging import get_logger
from src.sentiment.cryptopanic_client import fetch_and_score

logger = get_logger("sentiment_engine")


class SentimentEngine:
    """Periyodik olarak tum trading ciftleri icin sentiment analizi yapar."""

    def __init__(self, interval_seconds: int = 300) -> None:
        self.interval = interval_seconds  # Varsayilan: 5 dakika
        self._running = False

    async def start(self) -> None:
        """Sentiment guncelleme dongusu."""
        if not settings.cryptopanic_api_key:
            logger.info("sentiment_engine_disabled", reason="no_api_key")
            return

        self._running = True
        logger.info("sentiment_engine_started", interval=self.interval)

        while self._running:
            await self._update_all()
            await asyncio.sleep(self.interval)

    async def stop(self) -> None:
        self._running = False

    async def _update_all(self) -> None:
        """Tum ciftler icin sentiment guncelle."""
        for symbol in settings.trading_pairs:
            try:
                result = await fetch_and_score(symbol)
                if result:
                    logger.debug(
                        "sentiment_updated",
                        symbol=symbol,
                        score=result["score"],
                    )
            except Exception:
                logger.exception("sentiment_update_error", symbol=symbol)
