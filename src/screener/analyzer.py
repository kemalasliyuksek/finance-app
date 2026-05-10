"""Katman 2: Derin teknik analiz.

Screener adayları için mum verisi çeker, mevcut TA pipeline ile analiz eder.
Memory'de çalışır — DB'ye yazmaz.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from binance import AsyncClient

from src.analysis.ta_engine import TAResult, candles_to_dataframe, run_analysis
from src.collector.data_normalizer import normalize_klines_batch
from src.config import settings
from src.core.logging import get_logger
from src.core.rate_limiter import binance_limiter
from src.screener.scanner import ScanResult
from src.strategy.ema_crossover import EMACrossoverStrategy

logger = get_logger("screener.analyzer")

# Rate limit koruması: aynı anda max paralel API çağrısı
_BATCH_SIZE = 8
_BATCH_DELAY = 0.5  # batch'ler arası bekleme (saniye)


@dataclass
class AnalysisResult:
    """Derin analiz sonucu — TA skorlu."""

    symbol: str
    price: float
    change_24h: float
    volume_24h: float
    side: str               # BUY / SELL
    confidence: float       # 0.0 - 1.0
    ta_summary: dict        # Kısa TA özeti (dashboard için)
    scan_score: float       # Katman 1 composite skoru
    breakout_score: float = 0.0  # Breakout potansiyeli skoru (0-1)


class Analyzer:
    """Aday coinler için derin teknik analiz."""

    def __init__(self, client: AsyncClient) -> None:
        self.client = client
        self.strategy = EMACrossoverStrategy()

    async def analyze_batch(
        self, candidates: list[ScanResult], interval: str = "15m"
    ) -> list[AnalysisResult]:
        """Aday listesi için batch analiz yap.

        Her aday için 200 mum çeker ve full TA pipeline çalıştırır.
        Rate limit koruması için 8'li batch'ler halinde paralel çeker.
        """
        results: list[AnalysisResult] = []
        total = len(candidates)

        for batch_start in range(0, total, _BATCH_SIZE):
            batch = candidates[batch_start : batch_start + _BATCH_SIZE]
            batch_results = await asyncio.gather(
                *(self._analyze_single(c, interval) for c in batch),
                return_exceptions=True,
            )

            for i, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    logger.warning(
                        "analysis_failed",
                        symbol=batch[i].symbol,
                        error=str(result),
                    )
                elif result is not None:
                    results.append(result)

            # Rate limit koruması: batch'ler arası bekleme
            if batch_start + _BATCH_SIZE < total:
                await asyncio.sleep(_BATCH_DELAY)

        # Confidence + breakout ağırlıklı sırala
        bw = settings.screener_breakout_weight
        results.sort(
            key=lambda r: r.confidence * (1 - bw) + r.breakout_score * bw,
            reverse=True,
        )

        logger.info(
            "batch_analysis_complete",
            candidates=total,
            analyzed=len(results),
        )

        return results

    async def _analyze_single(
        self, candidate: ScanResult, interval: str
    ) -> AnalysisResult | None:
        """Tek bir coin için mum çek + TA analiz et."""
        try:
            # Rate limiter + Binance'den 200 mum çek
            await binance_limiter.acquire()
            klines = await self.client.get_klines(
                symbol=candidate.symbol, interval=interval, limit=200
            )
        except Exception:
            logger.exception("kline_fetch_error", symbol=candidate.symbol)
            return None

        if not klines or len(klines) < 30:
            return None

        # Normalize et (CandleCreate Pydantic objeleri)
        candle_creates = normalize_klines_batch(klines, candidate.symbol, interval)

        if len(candle_creates) < 30:
            return None

        # DataFrame'e dönüştür ve analiz yap
        df = candles_to_dataframe(candle_creates)
        ta_result = run_analysis(df, symbol=candidate.symbol, interval=interval)

        # Strateji değerlendirmesi (sentiment=None, screener'da yok)
        signal = self.strategy.evaluate(ta_result, sentiment_score=None)

        if signal is None:
            return None

        confidence = float(signal.confidence)

        # Minimum confidence filtresi — çok düşük skorları atla
        if confidence < settings.min_signal_confidence * 0.5:
            return None

        ta_summary = _build_ta_summary(ta_result)
        breakout_score = _calculate_breakout_score(ta_result)

        return AnalysisResult(
            symbol=candidate.symbol,
            price=candidate.price,
            change_24h=candidate.change_24h,
            volume_24h=candidate.volume_24h,
            side=signal.side,
            confidence=confidence,
            ta_summary=ta_summary,
            scan_score=candidate.composite_score,
            breakout_score=breakout_score,
        )


def _calculate_breakout_score(ta: TAResult) -> float:
    """Breakout potansiyeli skoru hesapla (0-1).

    Bileşenler:
    - BB squeeze (sıkışma): 0.4
    - Volume intensity (kademeli hacim): 0.3
    - RSI momentum buildup (güç birikimi): 0.3
    """
    score = 0.0

    # BB squeeze: sıkışma varsa patlama potansiyeli yüksek
    if ta.bollinger.get("bb_squeeze", False):
        score += 0.4

    # Volume intensity: kademeli hacim yoğunluğu
    intensity = ta.volume.get("volume_intensity", 0.0)
    score += intensity * 0.3

    # RSI momentum buildup: RSI 30-50 arasında ve yükseliyor
    rsi = ta.rsi.get("rsi")
    prev_rsi = ta.rsi.get("prev_rsi")
    if rsi is not None and prev_rsi is not None:
        if 30 <= rsi <= 55 and rsi > prev_rsi:
            # RSI yükseliyor ve güç birikiyor
            buildup_strength = min(1.0, (rsi - 30) / 25)  # 30'da 0, 55'te 1
            score += buildup_strength * 0.3

    return min(1.0, round(score, 4))


def _build_ta_summary(ta: TAResult) -> dict:
    """Dashboard için kısa TA özeti oluştur."""
    return {
        "ema_trend": ta.ema.get("trend"),
        "ema_crossover": ta.ema.get("crossover"),
        "rsi": ta.rsi.get("rsi"),
        "rsi_zone": ta.rsi.get("zone"),
        "bb_position": ta.bollinger.get("bb_position"),
        "bb_squeeze": ta.bollinger.get("bb_squeeze"),
        "volume_spike": ta.volume.get("is_spike"),
        "volume_ratio": ta.volume.get("volume_ratio"),
        "volume_intensity": ta.volume.get("volume_intensity"),
        "atr_pct": ta.atr.get("atr_pct"),
        "macd_crossover": ta.macd.get("macd_crossover"),
    }
