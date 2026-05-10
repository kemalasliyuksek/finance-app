"""Circuit breaker — Binance API arızasında koruma.

State machine: CLOSED → OPEN → HALF_OPEN → CLOSED
- CLOSED: Normal çalışma, hatalar sayılır
- OPEN: Tüm çağrılar anında reddedilir (recovery_timeout kadar)
- HALF_OPEN: Tek deneme çağrısı yapılır, başarılıysa CLOSED'a döner
"""

from __future__ import annotations

import asyncio
import time
from enum import StrEnum

from src.core.exceptions import BinanceAPIError
from src.core.logging import get_logger

logger = get_logger("circuit_breaker")


class CircuitState(StrEnum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """Binance API çağrıları için circuit breaker."""

    def __init__(
        self,
        name: str = "binance",
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
    ) -> None:
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: float = 0
        self._lock = asyncio.Lock()

    @property
    def state(self) -> CircuitState:
        """Mevcut durum (recovery timeout kontrolü ile)."""
        if self._state == CircuitState.OPEN:
            elapsed = time.monotonic() - self._last_failure_time
            if elapsed >= self.recovery_timeout:
                return CircuitState.HALF_OPEN
        return self._state

    async def call(self, func, *args, **kwargs):
        """Fonksiyonu circuit breaker koruması ile çağır."""
        async with self._lock:
            current_state = self.state

            if current_state == CircuitState.OPEN:
                logger.warning(
                    "circuit_breaker_open",
                    name=self.name,
                    failures=self._failure_count,
                    recovery_in=round(
                        self.recovery_timeout - (time.monotonic() - self._last_failure_time), 1
                    ),
                )
                raise BinanceAPIError(
                    f"Circuit breaker açık ({self.name}) — "
                    f"{self._failure_count} ardışık hata, "
                    f"{self.recovery_timeout}s sonra tekrar denenecek"
                )

            if current_state == CircuitState.HALF_OPEN:
                logger.info("circuit_breaker_half_open", name=self.name)

        # Çağrıyı lock dışında yap (blocking olmasın)
        try:
            result = await func(*args, **kwargs)
        except Exception as e:
            await self._on_failure(e)
            raise
        else:
            await self._on_success()
            return result

    async def _on_success(self) -> None:
        """Başarılı çağrı — state'i resetle."""
        async with self._lock:
            current = self.state  # property üzerinden kontrol (timeout hesabı)
            if current in (CircuitState.HALF_OPEN, CircuitState.CLOSED):
                if self._failure_count > 0:
                    logger.info(
                        "circuit_breaker_recovered",
                        name=self.name,
                        previous_failures=self._failure_count,
                    )
                self._failure_count = 0
                self._state = CircuitState.CLOSED

    async def _on_failure(self, error: Exception) -> None:
        """Başarısız çağrı — hata sayacını artır."""
        async with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.monotonic()

            if self._state == CircuitState.HALF_OPEN:
                # Half-open'da hata → tekrar open
                self._state = CircuitState.OPEN
                logger.warning(
                    "circuit_breaker_reopened",
                    name=self.name,
                    error=str(error),
                )
            elif self._failure_count >= self.failure_threshold:
                self._state = CircuitState.OPEN
                logger.error(
                    "circuit_breaker_tripped",
                    name=self.name,
                    failures=self._failure_count,
                    threshold=self.failure_threshold,
                    error=str(error),
                )


# Global instance — tüm Binance API çağrıları paylaşır
binance_circuit_breaker = CircuitBreaker(name="binance", failure_threshold=5, recovery_timeout=60.0)
