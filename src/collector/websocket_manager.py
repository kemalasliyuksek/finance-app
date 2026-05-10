"""Binance WebSocket ile anlık kline (mum) stream yönetimi."""

from __future__ import annotations

import asyncio
from typing import Any

from binance import AsyncClient, BinanceSocketManager

from src.collector.data_normalizer import normalize_kline
from src.config import settings
from src.core.events import publish
from src.core.logging import get_logger
from src.constants import RedisChannel
from src.db.repositories.candle_repo import CandleRepository
from src.db.session import get_session

logger = get_logger("websocket_manager")


class KlineWebSocketManager:
    """Binance WebSocket kline stream yöneticisi.

    Her trading çifti ve interval için ayrı WebSocket stream açar.
    Mum kapanışında Redis pub/sub ile bildirim yayınlar.
    """

    def __init__(self, client: AsyncClient) -> None:
        self.client = client
        self.bsm: BinanceSocketManager | None = None
        self._tasks: list[asyncio.Task] = []
        self._running = False

    async def start(self) -> None:
        """Tüm konfigüre edilmiş çiftler için WebSocket stream'leri başlat."""
        self.bsm = BinanceSocketManager(self.client)
        self._running = True

        for symbol in settings.trading_pairs:
            for interval in settings.candle_intervals:
                task = asyncio.create_task(
                    self._run_kline_stream(symbol, interval),
                    name=f"ws_{symbol}_{interval}",
                )
                self._tasks.append(task)

        logger.info(
            "websocket_streams_started",
            pairs=settings.trading_pairs,
            intervals=settings.candle_intervals,
            stream_count=len(self._tasks),
        )

    async def stop(self) -> None:
        """Tüm stream'leri durdur."""
        self._running = False
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()
        logger.info("websocket_streams_stopped")

    async def _run_kline_stream(self, symbol: str, interval: str) -> None:
        """Tek bir kline stream'ini yönet - otomatik yeniden bağlanma ile."""
        retry_count = 0
        max_retries = 10
        base_delay = 1.0

        while self._running:
            try:
                await self._consume_kline_stream(symbol, interval)
                retry_count = 0  # Başarılı bağlantı sonrası sıfırla
            except asyncio.CancelledError:
                logger.info("stream_cancelled", symbol=symbol, interval=interval)
                return
            except Exception:
                retry_count += 1
                if retry_count > max_retries:
                    logger.error(
                        "stream_max_retries_exceeded",
                        symbol=symbol,
                        interval=interval,
                        retries=retry_count,
                    )
                    return

                delay = min(base_delay * (2 ** (retry_count - 1)), 60.0)
                logger.warning(
                    "stream_reconnecting",
                    symbol=symbol,
                    interval=interval,
                    retry=retry_count,
                    delay=delay,
                )
                await asyncio.sleep(delay)

    async def _consume_kline_stream(self, symbol: str, interval: str) -> None:
        """Kline stream'ini tüket ve veritabanına yaz."""
        if not self.bsm:
            return

        socket = self.bsm.kline_socket(symbol=symbol, interval=interval)

        async with socket as stream:
            logger.info("stream_connected", symbol=symbol, interval=interval)
            async for msg in stream:
                if not self._running:
                    break
                await self._process_kline_message(msg, symbol, interval)

    async def _process_kline_message(
        self, msg: dict[str, Any], symbol: str, interval: str
    ) -> None:
        """Tek bir kline mesajını işle."""
        if msg.get("e") == "error":
            logger.error("ws_error", symbol=symbol, interval=interval, error=msg)
            return

        kline = msg.get("k")
        if not kline:
            return

        is_closed = kline.get("x", False)

        try:
            candle = normalize_kline(msg, symbol, interval)
        except Exception:
            logger.exception("kline_normalize_error", symbol=symbol, interval=interval)
            return

        # Veritabanına yaz (her güncelleme)
        try:
            async with get_session() as session:
                repo = CandleRepository(session)
                await repo.upsert(candle)
        except Exception:
            logger.exception("candle_db_error", symbol=symbol, interval=interval)

        # Mum kapandıysa sinyal üretimi için event yayınla
        if is_closed:
            channel = RedisChannel.candle_closed(symbol, interval)
            await publish(
                channel,
                {
                    "symbol": symbol,
                    "interval": interval,
                    "close": str(candle.close),
                    "volume": str(candle.volume),
                    "open_time": candle.open_time.isoformat(),
                    "close_time": candle.close_time.isoformat(),
                },
            )
            logger.debug(
                "candle_closed",
                symbol=symbol,
                interval=interval,
                close=str(candle.close),
            )
