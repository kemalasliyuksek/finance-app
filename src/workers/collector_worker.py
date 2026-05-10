"""Veri toplama worker - WebSocket + tarihsel veri backfill."""

from __future__ import annotations

import asyncio

from src.collector.rest_fetcher import backfill_all_pairs, create_binance_client
from src.collector.websocket_manager import KlineWebSocketManager
from src.core.logging import get_logger
from src.db.repositories.candle_repo import CandleRepository
from src.db.session import get_session

logger = get_logger("collector_worker")


async def run_collector() -> None:
    """Ana veri toplama döngüsü.

    1. Binance client oluştur
    2. Tarihsel veri backfill yap (indikatörler için yeterli geçmiş)
    3. WebSocket stream'lerini başlat
    """
    logger.info("collector_worker_starting")

    client = await create_binance_client()

    try:
        # 1) Tarihsel veri backfill
        logger.info("starting_backfill")
        results = await backfill_all_pairs(client)

        # Backfill sonuçlarını DB'ye yaz
        async with get_session() as session:
            repo = CandleRepository(session)
            from src.collector.rest_fetcher import fetch_historical_klines

            for symbol_interval, count in results.items():
                symbol, interval = symbol_interval.rsplit("_", 1)
                if count > 0:
                    candles = await fetch_historical_klines(client, symbol, interval)
                    saved = await repo.upsert_many(candles)
                    logger.info(
                        "backfill_saved",
                        symbol=symbol,
                        interval=interval,
                        count=saved,
                    )

        # 2) WebSocket stream'lerini başlat
        ws_manager = KlineWebSocketManager(client)
        await ws_manager.start()

        # Stream'ler çalışırken bekle
        logger.info("collector_running")
        while True:
            await asyncio.sleep(60)

    except asyncio.CancelledError:
        logger.info("collector_worker_cancelled")
    except Exception:
        logger.exception("collector_worker_error")
    finally:
        await client.close_connection()
        logger.info("collector_worker_stopped")
