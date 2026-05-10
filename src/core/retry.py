"""Retry logic — exponential backoff ile yeniden deneme."""

from __future__ import annotations

import asyncio
import functools
from typing import Any

from src.core.logging import get_logger

logger = get_logger("retry")


def with_retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    retryable_exceptions: tuple = (Exception,),
):
    """Async fonksiyonlar için exponential backoff retry dekoratörü.

    Args:
        max_retries: Maksimum deneme sayısı (ilk çağrı dahil değil)
        base_delay: İlk bekleme süresi (saniye)
        max_delay: Maksimum bekleme süresi (saniye)
        retryable_exceptions: Tekrar denenecek exception türleri
    """

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e

                    if attempt >= max_retries:
                        logger.error(
                            "retry_exhausted",
                            function=func.__name__,
                            attempts=attempt + 1,
                            error=str(e),
                        )
                        raise

                    delay = min(base_delay * (2 ** attempt), max_delay)
                    logger.warning(
                        "retry_attempt",
                        function=func.__name__,
                        attempt=attempt + 1,
                        max_retries=max_retries,
                        delay=round(delay, 2),
                        error=str(e),
                    )
                    await asyncio.sleep(delay)

            raise last_exception  # type: ignore[misc]

        return wrapper

    return decorator
