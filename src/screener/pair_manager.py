"""Aktif trading pair yönetimi.

Screener sonuçlarına göre pair listesini dinamik günceller.
Açık pozisyonu olan coinleri ASLA çıkarmaz.
"""

from __future__ import annotations

import asyncio

from binance import AsyncClient

from src.collector.rest_fetcher import fetch_historical_klines
from src.collector.rest_poller import RestPoller
from src.config import settings
from src.constants import RedisChannel
from src.core.events import publish
from src.core.logging import get_logger
from src.db.repositories.candle_repo import CandleRepository
from src.db.repositories.trade_repo import TradeRepository
from src.db.session import get_session
from src.screener.analyzer import AnalysisResult
from src.screener.scanner import ScanResult
from src.strategy.signal_generator import SignalGenerator

logger = get_logger("screener.pair_manager")


class PairManager:
    """Aktif trading pair listesini yönetir.

    Kurallar:
    - Top N hacimli coin her zaman aktif (screener sonucu ne olursa olsun)
    - Screener'dan en iyi M coin dinamik olarak eklenir
    - Açık pozisyonu olan coin ASLA çıkarılmaz
    """

    def __init__(
        self,
        client: AsyncClient,
        poller: RestPoller,
        signal_gen: SignalGenerator,
    ) -> None:
        self.client = client
        self.poller = poller
        self.signal_gen = signal_gen
        self._lock = asyncio.Lock()
        self._active_pairs: set[str] = set(settings.trading_pairs)
        self._volume_top: set[str] = set()
        self._dynamic: set[str] = set()

    @property
    def active_pairs(self) -> set[str]:
        return self._active_pairs.copy()

    @property
    def volume_top_pairs(self) -> list[str]:
        return sorted(self._volume_top)

    @property
    def dynamic_pairs(self) -> list[str]:
        return sorted(self._dynamic)

    async def update_pairs(
        self,
        volume_top: list[ScanResult],
        scan_results: list[ScanResult],
        analysis_results: list[AnalysisResult],
    ) -> dict:
        """Screener sonuçlarına göre aktif pair listesini güncelle.

        Args:
            volume_top: Hacim bazında top N (momentum filtresi yok, BTC/ETH dahil)
            scan_results: Momentum filtreli adaylar
            analysis_results: Derin TA analizi geçen coinler

        Returns:
            {"added": [...], "removed": [...], "protected": [...], "active": [...]}
        """
        async with self._lock:
            return await self._do_update(volume_top, scan_results, analysis_results)

    async def _do_update(
        self,
        volume_top: list[ScanResult],
        scan_results: list[ScanResult],
        analysis_results: list[AnalysisResult],
    ) -> dict:
        # 1) Hacim top N (scanner'dan filtresiz olarak geliyor)
        new_volume_top = {r.symbol for r in volume_top}

        # 2) TA skor top M (confidence sıralı, zaten analyzer'dan sıralı geliyor)
        max_dynamic = settings.screener_active_dynamic_pairs
        new_dynamic = set()
        for result in analysis_results:
            if result.symbol not in new_volume_top and len(new_dynamic) < max_dynamic:
                new_dynamic.add(result.symbol)

        desired = new_volume_top | new_dynamic

        # 3) Açık pozisyon koruması — açık trade'i olan coin her zaman aktif
        protected = await self._get_protected_symbols()
        desired = desired | protected  # Korunan coinleri de desired'a ekle

        # 4) Diff hesapla
        current = self._active_pairs
        to_remove = current - desired
        to_add = desired - current

        # 5) Çıkarmaları uygula
        removed = []
        for symbol in to_remove:
            try:
                await self._remove_pair(symbol)
                removed.append(symbol)
            except Exception:
                logger.exception("pair_remove_error", symbol=symbol)

        # 6) Eklemeleri uygula (backfill + poller + signal gen)
        added = []
        for symbol in to_add:
            try:
                await self._add_pair(symbol)
                added.append(symbol)
            except Exception:
                logger.exception("pair_add_error", symbol=symbol)

        # 7) State güncelle
        self._volume_top = new_volume_top
        self._dynamic = new_dynamic
        self._active_pairs = (current - set(removed)) | set(added)

        # 8) Config güncelle
        settings.trading_pairs = sorted(self._active_pairs)

        # 9) Redis event
        await publish(
            RedisChannel.CONFIG_PAIRS_UPDATED,
            {
                "pairs": sorted(self._active_pairs),
                "added": added,
                "removed": removed,
                "source": "screener",
            },
        )

        logger.info(
            "pairs_updated",
            active=len(self._active_pairs),
            added=added,
            removed=removed,
            protected=sorted(protected & current - desired) if protected else [],
            volume_top=sorted(new_volume_top),
            dynamic=sorted(new_dynamic),
        )

        return {
            "added": added,
            "removed": removed,
            "protected": sorted(protected),
            "active": sorted(self._active_pairs),
        }

    async def _get_protected_symbols(self) -> set[str]:
        """Açık pozisyonu olan sembolleri getir — bu coinler ASLA çıkarılmaz."""
        try:
            async with get_session() as session:
                repo = TradeRepository(session)
                open_trades = await repo.get_open_trades()
                return {t.symbol for t in open_trades}
        except Exception:
            logger.exception("protected_symbols_query_error")
            # Hata durumunda güvenli taraf: hiçbir şeyi çıkarma
            return self._active_pairs

    async def _add_pair(self, symbol: str) -> None:
        """Yeni coini pipeline'a ekle: backfill + poller + signal gen."""
        logger.info("adding_pair", symbol=symbol)

        # 1) Tarihsel veri backfill
        for interval in settings.candle_intervals:
            try:
                candles = await fetch_historical_klines(
                    self.client, symbol, interval
                )
                async with get_session() as session:
                    repo = CandleRepository(session)
                    count = await repo.upsert_many(candles)
                    logger.info(
                        "pair_backfill_complete",
                        symbol=symbol,
                        interval=interval,
                        count=count,
                    )
            except Exception:
                logger.exception(
                    "pair_backfill_error", symbol=symbol, interval=interval
                )

        # 2) Polling başlat
        await self.poller.add_pair(symbol)

        # 3) Signal generator subscribe
        await self.signal_gen.subscribe_pair(symbol)

    async def _remove_pair(self, symbol: str) -> None:
        """Coini pipeline'dan çıkar: poller + signal gen durdur."""
        logger.info("removing_pair", symbol=symbol)

        await self.poller.remove_pair(symbol)
        await self.signal_gen.unsubscribe_pair(symbol)
