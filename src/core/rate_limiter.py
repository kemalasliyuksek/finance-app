"""Binance API rate limiter — tüm worker'lar paylaşır."""

from __future__ import annotations

import asyncio
import time

from src.core.logging import get_logger

logger = get_logger("rate_limiter")


class BinanceRateLimiter:
    """Token bucket algoritması ile Binance API istek hız sınırlayıcı.

    Binance limiti: 1200 istek/dakika (IP bazlı).
    Varsayılan: 10 istek/saniye (%50 güvenlik marjı).
    """

    def __init__(self, max_per_second: float = 10.0) -> None:
        self._max_tokens = max_per_second
        self._tokens = max_per_second
        self._interval = 1.0 / max_per_second
        self._last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Bir istek için token al. Token yoksa bekle."""
        async with self._lock:
            self._refill()
            while self._tokens < 1:
                wait_time = self._interval
                await asyncio.sleep(wait_time)
                self._refill()
            self._tokens -= 1

    def _refill(self) -> None:
        """Geçen süreye göre token'ları yenile."""
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(self._max_tokens, self._tokens + elapsed * self._max_tokens)
        self._last_refill = now


# Tüm worker'ların paylaştığı tek instance
binance_limiter = BinanceRateLimiter(max_per_second=10.0)
