"""Katman 1: Hızlı piyasa taraması.

Binance ticker/24hr ile tüm USDT çiftlerini çeker,
filtreleyip composite skor ile sıralar.
Tek API çağrısı — rate limit maliyeti minimal.
"""

from __future__ import annotations

from dataclasses import dataclass

from binance import AsyncClient

from src.config import settings
from src.core.logging import get_logger
from src.screener.filters import filter_tickers

logger = get_logger("screener.scanner")


@dataclass
class ScanResult:
    """Filtrelenmiş ve skorlanmış tarama sonucu."""

    symbol: str
    price: float
    change_24h: float          # Fiyat değişimi (%)
    volume_24h: float          # 24s USDT hacmi
    volume_score: float        # Normalize edilmiş hacim skoru (0-1)
    momentum_score: float      # Normalize edilmiş momentum skoru (0-1)
    composite_score: float     # Ağırlıklı bileşik skor


class Scanner:
    """Binance ticker/24hr ile hızlı piyasa taraması."""

    def __init__(self, client: AsyncClient) -> None:
        self.client = client

    async def scan(self) -> tuple[list[ScanResult], list[ScanResult]]:
        """Tüm USDT çiftlerini tara, filtrele, skorla.

        Returns:
            (candidates, volume_top): Filtrelenmiş adaylar + hacim top N (filtresiz).
        """
        try:
            tickers = await self.client.get_ticker()
        except Exception:
            logger.exception("ticker_fetch_error")
            return [], []

        if not tickers:
            logger.warning("no_tickers_returned")
            return [], []

        # Hacim top N — momentum filtresi OLMADAN, sadece temel filtreler
        # BTC, ETH gibi büyük coinler %2 hareket etmese bile her zaman izlenmeli
        volume_top = self._get_volume_top(tickers)

        # Momentum filtreli adaylar (dinamik coin keşfi için)
        filtered = filter_tickers(tickers)
        results = self._score_tickers(filtered) if filtered else []

        # Sırala ve max aday sayısına kırp
        results.sort(key=lambda r: r.composite_score, reverse=True)
        max_candidates = settings.screener_max_candidates
        results = results[:max_candidates]

        logger.info(
            "scan_complete",
            total_tickers=len(tickers),
            after_filter=len(filtered),
            returned=len(results),
            volume_top=[r.symbol for r in volume_top],
        )

        return results, volume_top

    def _get_volume_top(self, tickers: list[dict]) -> list[ScanResult]:
        """Hacim bazında top N coini getir — momentum filtresi UYGULANMAZ.

        Sadece temel filtreler: USDT çifti, kaldıraçlı değil, stablecoin değil.
        """
        from src.screener.filters import is_usdt_pair, is_leveraged_token, is_stablecoin_pair, is_blacklisted

        valid = []
        for t in tickers:
            symbol = t.get("symbol", "")
            if not is_usdt_pair(symbol):
                continue
            if is_leveraged_token(symbol):
                continue
            if is_stablecoin_pair(symbol):
                continue
            if is_blacklisted(symbol):
                continue
            try:
                volume = float(t.get("quoteVolume", 0))
                if volume < settings.screener_volume_top_min_usdt:
                    continue
                price = float(t.get("lastPrice", 0))
                change = float(t.get("priceChangePercent", 0))
                valid.append(ScanResult(
                    symbol=symbol,
                    price=price,
                    change_24h=change,
                    volume_24h=volume,
                    volume_score=0,
                    momentum_score=0,
                    composite_score=0,
                ))
            except (ValueError, TypeError):
                continue

        valid.sort(key=lambda r: r.volume_24h, reverse=True)
        return valid[:settings.screener_volume_top_n]

    def _score_tickers(self, tickers: list[dict]) -> list[ScanResult]:
        """Ticker'lara composite skor ata."""
        # Normalizasyon için max değerleri bul
        volumes = []
        changes = []

        for t in tickers:
            try:
                volumes.append(float(t.get("quoteVolume", 0)))
                changes.append(abs(float(t.get("priceChangePercent", 0))))
            except (ValueError, TypeError):
                volumes.append(0)
                changes.append(0)

        max_vol = max(volumes) if volumes else 1
        max_change = max(changes) if changes else 1

        results = []
        for i, ticker in enumerate(tickers):
            try:
                symbol = ticker["symbol"]
                price = float(ticker.get("lastPrice", 0))
                change = float(ticker.get("priceChangePercent", 0))
                volume = float(ticker.get("quoteVolume", 0))

                # Normalize [0, 1]
                vol_score = volumes[i] / max_vol if max_vol > 0 else 0
                mom_score = changes[i] / max_change if max_change > 0 else 0

                # Composite: hacim + momentum (ağırlıklar config'den)
                composite = (
                    vol_score * settings.screener_composite_volume_weight
                    + mom_score * settings.screener_composite_momentum_weight
                )

                results.append(ScanResult(
                    symbol=symbol,
                    price=price,
                    change_24h=change,
                    volume_24h=volume,
                    volume_score=round(vol_score, 4),
                    momentum_score=round(mom_score, 4),
                    composite_score=round(composite, 4),
                ))
            except (KeyError, ValueError, TypeError):
                continue

        return results

    def get_volume_top(self, tickers: list[dict] | None = None, results: list[ScanResult] | None = None) -> list[str]:
        """Hacim top N sembollerini döndür.

        results parametresi verilmişse ondan, yoksa tickers'dan hesaplar.
        """
        n = settings.screener_volume_top_n

        if results:
            by_volume = sorted(results, key=lambda r: r.volume_24h, reverse=True)
            return [r.symbol for r in by_volume[:n]]

        return []
