"""REST polling ile periyodik mum verisi çekme - WebSocket alternatifi.

Binance testnet WebSocket kararsız olduğu için REST polling kullanılır.
Her interval için uygun aralıkta son mumları çeker ve DB'ye yazar.
Mum kapandığında Redis event yayınlar (sinyal üretimi için).
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from binance import AsyncClient

from src.collector.data_normalizer import normalize_klines_batch
from src.config import settings
from src.constants import RedisChannel
from src.core.events import publish
from src.core.logging import get_logger
from src.db.repositories.candle_repo import CandleRepository
from src.db.session import get_session

logger = get_logger("rest_poller")

# Interval -> polling sıklığı (saniye)
POLL_INTERVALS = {
    "1m": 10,
    "5m": 30,
    "15m": 60,      # Her dakika kontrol et
    "1h": 120,      # Her 2 dakikada kontrol et
    "4h": 300,
    "1d": 600,
}


class RestPoller:
    """REST API ile periyodik mum verisi çekme."""

    def __init__(self, client: AsyncClient) -> None:
        self.client = client
        self._running = False
        self._tasks: dict[str, asyncio.Task] = {}  # key: "{symbol}_{interval}"
        # Son bilinen kapanmış mum zamanı (yeni mum tespiti için)
        self._last_closed: dict[str, datetime] = {}

    async def start(self) -> None:
        """Tüm çiftler ve interval'ler için polling başlat."""
        self._running = True

        for symbol in settings.trading_pairs:
            for interval in settings.candle_intervals:
                key = f"{symbol}_{interval}"
                task = asyncio.create_task(
                    self._poll_loop(symbol, interval),
                    name=f"poll_{key}",
                )
                self._tasks[key] = task

        logger.info(
            "rest_poller_started",
            pairs=settings.trading_pairs,
            intervals=settings.candle_intervals,
            stream_count=len(self._tasks),
        )

    async def stop(self) -> None:
        """Tüm polling'leri durdur."""
        self._running = False
        for task in self._tasks.values():
            task.cancel()
        await asyncio.gather(*self._tasks.values(), return_exceptions=True)
        self._tasks.clear()
        logger.info("rest_poller_stopped")

    async def add_pair(self, symbol: str) -> None:
        """Yeni çift için polling başlat (tüm interval'ler)."""
        for interval in settings.candle_intervals:
            key = f"{symbol}_{interval}"
            if key in self._tasks:
                continue  # Zaten aktif
            task = asyncio.create_task(
                self._poll_loop(symbol, interval),
                name=f"poll_{key}",
            )
            self._tasks[key] = task

        logger.info("poller_pair_added", symbol=symbol)

    async def remove_pair(self, symbol: str) -> None:
        """Çift için polling durdur (tüm interval'ler)."""
        for interval in settings.candle_intervals:
            key = f"{symbol}_{interval}"
            task = self._tasks.pop(key, None)
            if task:
                task.cancel()
            self._last_closed.pop(key, None)

        logger.info("poller_pair_removed", symbol=symbol)

    async def _poll_loop(self, symbol: str, interval: str) -> None:
        """Tek bir çift/interval için polling döngüsü."""
        poll_seconds = POLL_INTERVALS.get(interval, 60)
        key = f"{symbol}_{interval}"

        while self._running:
            try:
                await self._fetch_and_store(symbol, interval, key)
            except asyncio.CancelledError:
                return
            except Exception:
                logger.exception("poll_error", symbol=symbol, interval=interval)

            await asyncio.sleep(poll_seconds)

    async def _fetch_and_store(self, symbol: str, interval: str, key: str) -> None:
        """Son mumları çek, DB'ye yaz, kapanmış mum varsa event yayınla."""
        # Son 5 mumu çek (güncel + öncekiler)
        klines = await self.client.get_klines(
            symbol=symbol, interval=interval, limit=5
        )

        if not klines:
            return

        candles = normalize_klines_batch(klines, symbol, interval)

        # DB'ye yaz
        async with get_session() as session:
            repo = CandleRepository(session)
            for candle in candles:
                await repo.upsert(candle)

        # Kapanmış mum kontrolü (son öncesi mumlar kapanmış demektir)
        # Son eleman henüz kapanmamış mevcut mum
        closed_candles = candles[:-1]

        if closed_candles:
            latest_closed = closed_candles[-1]
            prev_closed_time = self._last_closed.get(key)

            if prev_closed_time is None or latest_closed.close_time > prev_closed_time:
                self._last_closed[key] = latest_closed.close_time

                # Yeni kapanmış mum — sinyal üretimi için event yayınla
                channel = RedisChannel.candle_closed(symbol, interval)
                await publish(
                    channel,
                    {
                        "symbol": symbol,
                        "interval": interval,
                        "close": str(latest_closed.close),
                        "volume": str(latest_closed.volume),
                        "open_time": latest_closed.open_time.isoformat(),
                        "close_time": latest_closed.close_time.isoformat(),
                    },
                )
                logger.info(
                    "candle_closed_detected",
                    symbol=symbol,
                    interval=interval,
                    close=str(latest_closed.close),
                    close_time=latest_closed.close_time.isoformat(),
                )
