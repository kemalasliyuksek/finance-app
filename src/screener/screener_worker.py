"""Screener ana döngüsü — periyodik piyasa taraması.

Her cycle:
1. Scanner → ticker/24hr ile filtrele (top 30-40)
2. Analyzer → batch mum çek + full TA (memory'de)
3. PairManager → aktif pair listesini güncelle (sadece live modda)
4. Redis'e cache + event publish

Screener her zaman mainnet verisi kullanır (public endpoint, key gerektirmez).
Testnet modunda tarama ve analiz yapılır ama pipeline'a dokunulmaz.
"""

from __future__ import annotations

import asyncio
import time

from binance import AsyncClient

from src.collector.rest_poller import RestPoller
from src.config import settings
from src.constants import RedisChannel
from src.core.events import publish, set_cache
from src.core.logging import get_logger
from src.screener.analyzer import Analyzer
from src.screener.pair_manager import PairManager
from src.screener.scanner import Scanner
from src.strategy.signal_generator import SignalGenerator

logger = get_logger("screener.worker")


async def _create_mainnet_client() -> AsyncClient:
    """Screener için mainnet read-only client oluştur.

    Public endpoint'ler (ticker, klines) API key gerektirmez.
    Testnet modunda bile mainnet verisi kullanılır.
    """
    return await AsyncClient.create()


class ScreenerWorker:
    """Periyodik piyasa tarama worker'ı."""

    def __init__(
        self,
        client: AsyncClient,
        poller: RestPoller,
        signal_gen: SignalGenerator,
    ) -> None:
        self._trading_client = client  # Testnet/live — pipeline işlemleri için
        self._mainnet_client: AsyncClient | None = None
        self._poller = poller
        self._signal_gen = signal_gen
        self.pair_manager: PairManager | None = None
        self.scanner: Scanner | None = None
        self.analyzer: Analyzer | None = None
        self._running = False

    async def start(self) -> None:
        """Screener döngüsünü başlat."""
        self._running = True
        interval = settings.screener_interval_seconds

        # Mainnet client oluştur (tarama + analiz için)
        self._mainnet_client = await _create_mainnet_client()
        self.scanner = Scanner(self._mainnet_client)
        self.analyzer = Analyzer(self._mainnet_client)
        self.pair_manager = PairManager(
            self._trading_client, self._poller, self._signal_gen
        )

        is_live = not settings.is_testnet

        logger.info(
            "screener_worker_starting",
            interval_seconds=interval,
            min_volume=settings.screener_min_volume_usdt,
            min_change=settings.screener_min_change_pct,
            max_candidates=settings.screener_max_candidates,
            volume_top_n=settings.screener_volume_top_n,
            dynamic_pairs=settings.screener_active_dynamic_pairs,
            pair_management="active" if is_live else "view_only (testnet)",
        )

        # İlk çalıştırmayı biraz ertele — diğer worker'lar başlasın
        await asyncio.sleep(30)

        while self._running:
            try:
                await self._run_cycle()
            except asyncio.CancelledError:
                return
            except Exception:
                logger.exception("screener_cycle_error")

            await asyncio.sleep(interval)

    async def stop(self) -> None:
        """Screener döngüsünü durdur."""
        self._running = False
        if self._mainnet_client:
            await self._mainnet_client.close_connection()
        logger.info("screener_worker_stopped")

    async def _run_cycle(self) -> None:
        """Tek bir tarama döngüsü."""
        cycle_start = time.monotonic()

        # Katman 1: Hızlı tarama (her zaman mainnet)
        scan_results, volume_top = await self.scanner.scan()

        if not scan_results and not volume_top:
            logger.warning("scan_returned_no_results")
            return

        # Katman 2: Derin analiz (her zaman mainnet)
        analysis_results = await self.analyzer.analyze_batch(scan_results)

        # Katman 3: Pair listesini güncelle (sadece live/sandbox modda)
        update_result = {"added": [], "removed": [], "active": [], "protected": []}
        if not settings.is_testnet:
            update_result = await self.pair_manager.update_pairs(
                volume_top, scan_results, analysis_results
            )
        else:
            logger.debug(
                "testnet_mode_skip_pair_update",
                msg="Testnet modunda pipeline degistirilmez, sadece sonuclar gosterilir",
            )

        cycle_duration = time.monotonic() - cycle_start

        # Redis'e cache (dashboard API için — her modda çalışır)
        await self._cache_results(scan_results, analysis_results, cycle_duration)

        logger.info(
            "screener_cycle_complete",
            duration_seconds=round(cycle_duration, 2),
            scanned=len(scan_results),
            analyzed=len(analysis_results),
            active_pairs=len(update_result.get("active", [])),
            added=len(update_result.get("added", [])),
            removed=len(update_result.get("removed", [])),
            mode="live" if not settings.is_testnet else "view_only",
        )

    async def _cache_results(
        self,
        scan_results: list,
        analysis_results: list,
        cycle_duration: float,
    ) -> None:
        """Sonuçları Redis'e cache'le — API endpoint'i buradan okur."""
        from datetime import datetime, timezone

        # Aktif pair bilgisi (testnet'te pipeline güncellenmez ama mevcut pair'lar gösterilir)
        active_pairs = set(settings.trading_pairs)
        volume_top_pairs = []
        dynamic_pairs = []

        if self.pair_manager and not settings.is_testnet:
            active_pairs = self.pair_manager.active_pairs
            volume_top_pairs = self.pair_manager.volume_top_pairs
            dynamic_pairs = self.pair_manager.dynamic_pairs

        # Analiz sonuçları
        results_data = []
        for r in analysis_results:
            results_data.append({
                "symbol": r.symbol,
                "price": r.price,
                "change_24h": r.change_24h,
                "volume_24h": r.volume_24h,
                "side": r.side,
                "confidence": r.confidence,
                "ta_summary": r.ta_summary,
                "scan_score": r.scan_score,
                "is_active": r.symbol in active_pairs,
                "is_volume_top": False,  # Testnet'te anlamsız
            })

        await set_cache(
            "screener:latest_results",
            {"results": results_data, "total_scanned": len(scan_results)},
            ttl_seconds=settings.screener_interval_seconds * 2,
        )

        # Durum bilgisi
        status_data = {
            "enabled": True,
            "last_scan_at": datetime.now(timezone.utc).isoformat(),
            "cycle_duration_seconds": round(cycle_duration, 2),
            "total_pairs_scanned": len(scan_results),
            "candidates_analyzed": len(analysis_results),
            "active_pairs": sorted(active_pairs),
            "volume_top_pairs": volume_top_pairs,
            "dynamic_pairs": dynamic_pairs,
            "mode": "live" if not settings.is_testnet else "testnet",
        }

        await set_cache(
            "screener:status",
            status_data,
            ttl_seconds=settings.screener_interval_seconds * 2,
        )

        # WebSocket event (dashboard real-time)
        await publish(
            RedisChannel.SCREENER_RESULTS,
            {"type": "screener_update", "candidates": len(analysis_results)},
        )
