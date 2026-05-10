"""Binance REST API ile tarihsel mum verisi çekme."""

from __future__ import annotations

from binance import AsyncClient

from src.collector.data_normalizer import normalize_klines_batch
from src.config import settings
from src.core.logging import get_logger
from src.core.rate_limiter import binance_limiter
from src.schemas.candle import CandleCreate

logger = get_logger("rest_fetcher")

# Interval -> başlangıç için gereken mum sayısı (indikatörler için yeterli geçmiş)
BACKFILL_COUNTS = {
    "1m": 500,
    "5m": 500,
    "15m": 300,
    "1h": 300,
    "4h": 200,
    "1d": 200,
}


async def create_binance_client() -> AsyncClient:
    """Binance async client oluştur (sandbox/live/testnet)."""
    if settings.is_testnet:
        client = await AsyncClient.create(
            api_key=settings.binance_testnet_api_key,
            api_secret=settings.binance_testnet_api_secret,
            testnet=True,
        )
    elif settings.is_sandbox:
        # Sandbox: mainnet public data (key gerekmez)
        client = await AsyncClient.create()
    else:
        client = await AsyncClient.create(
            api_key=settings.binance_api_key,
            api_secret=settings.binance_api_secret,
        )
    return client


async def fetch_historical_klines(
    client: AsyncClient,
    symbol: str,
    interval: str,
    limit: int | None = None,
) -> list[CandleCreate]:
    """Tarihsel kline verisini çek ve normalize et.

    Args:
        client: Binance AsyncClient
        symbol: Trading çifti (örn: BTCUSDT)
        interval: Zaman dilimi (örn: 15m, 1h)
        limit: Çekilecek mum sayısı (None ise varsayılan kullanılır)

    Returns:
        Normalize edilmiş CandleCreate listesi
    """
    count = limit or BACKFILL_COUNTS.get(interval, 300)

    logger.info(
        "fetching_historical_klines",
        symbol=symbol,
        interval=interval,
        count=count,
    )

    await binance_limiter.acquire()
    klines = await client.get_klines(
        symbol=symbol,
        interval=interval,
        limit=count,
    )

    candles = normalize_klines_batch(klines, symbol, interval)

    logger.info(
        "historical_klines_fetched",
        symbol=symbol,
        interval=interval,
        count=len(candles),
    )

    return candles


async def backfill_all_pairs(client: AsyncClient) -> dict[str, int]:
    """Tüm trading çiftleri için tarihsel veri çek.

    Returns:
        {symbol_interval: candle_count} dictionary
    """
    results: dict[str, int] = {}

    for symbol in settings.trading_pairs:
        for interval in settings.candle_intervals:
            key = f"{symbol}_{interval}"
            try:
                candles = await fetch_historical_klines(client, symbol, interval)
                results[key] = len(candles)
            except Exception:
                logger.exception(
                    "backfill_failed", symbol=symbol, interval=interval
                )
                results[key] = 0

    return results
