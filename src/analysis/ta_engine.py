"""Teknik Analiz Motoru - tüm indikatörleri orkestre eder."""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from src.analysis.indicators import (
    calculate_atr,
    calculate_bollinger_bands,
    calculate_ema,
    calculate_macd,
    calculate_rsi,
    calculate_volume,
)
from src.config import settings
from src.core.logging import get_logger

logger = get_logger("ta_engine")


@dataclass
class TAResult:
    """Tüm teknik analiz sonuçlarını barındıran yapı."""

    ema: dict = field(default_factory=dict)
    rsi: dict = field(default_factory=dict)
    bollinger: dict = field(default_factory=dict)
    volume: dict = field(default_factory=dict)
    atr: dict = field(default_factory=dict)
    macd: dict = field(default_factory=dict)
    current_price: float = 0.0
    symbol: str = ""
    interval: str = ""
    recent_high: float | None = None   # Son N mumun en yüksek fiyatı (trailing stop için)
    recent_low: float | None = None    # Son N mumun en düşük fiyatı

    def to_dict(self) -> dict:
        """JSONB olarak saklanabilecek dict döndür."""
        return {
            "ema": self.ema,
            "rsi": self.rsi,
            "bollinger": self.bollinger,
            "volume": self.volume,
            "atr": self.atr,
            "macd": self.macd,
            "current_price": self.current_price,
        }


def candles_to_dataframe(candles: list) -> pd.DataFrame:
    """SQLAlchemy Candle nesnelerini pandas DataFrame'e dönüştür."""
    if not candles:
        return pd.DataFrame()

    data = []
    for c in candles:
        data.append(
            {
                "open_time": c.open_time,
                "open": float(c.open),
                "high": float(c.high),
                "low": float(c.low),
                "close": float(c.close),
                "volume": float(c.volume),
            }
        )

    df = pd.DataFrame(data)
    df.set_index("open_time", inplace=True)
    df.sort_index(inplace=True)
    return df


def run_analysis(df: pd.DataFrame, symbol: str = "", interval: str = "") -> TAResult:
    """Tüm teknik indikatörleri hesapla ve TAResult döndür.

    Args:
        df: OHLCV DataFrame (open, high, low, close, volume kolonları)
        symbol: Trading çifti (loglama için)
        interval: Zaman dilimi (loglama için)

    Returns:
        TAResult: Tüm indikatör sonuçları
    """
    if df.empty or len(df) < 30:
        logger.warning(
            "insufficient_data_for_analysis",
            symbol=symbol,
            interval=interval,
            candle_count=len(df),
        )
        return TAResult(symbol=symbol, interval=interval)

    result = TAResult(
        symbol=symbol,
        interval=interval,
        current_price=float(df["close"].iloc[-1]),
    )

    # Recent high/low (trailing stop için)
    lookback = min(settings.trailing_stop_lookback, len(df))
    if lookback > 0:
        result.recent_high = float(df["high"].iloc[-lookback:].max())
        result.recent_low = float(df["low"].iloc[-lookback:].min())

    try:
        result.ema = calculate_ema(
            df,
            fast_period=settings.ema_fast_period,
            slow_period=settings.ema_slow_period,
        )
    except Exception:
        logger.exception("ema_calculation_error", symbol=symbol)

    try:
        result.rsi = calculate_rsi(df, period=settings.rsi_period)
    except Exception:
        logger.exception("rsi_calculation_error", symbol=symbol)

    try:
        result.bollinger = calculate_bollinger_bands(
            df,
            period=settings.bb_period,
            std_dev=settings.bb_std_dev,
            squeeze_lookback=settings.bb_squeeze_lookback,
            squeeze_percentile=settings.bb_squeeze_percentile,
        )
    except Exception:
        logger.exception("bb_calculation_error", symbol=symbol)

    try:
        result.volume = calculate_volume(
            df,
            spike_mult=settings.volume_spike_multiplier,
            max_ratio=settings.volume_breakout_max_ratio,
        )
    except Exception:
        logger.exception("volume_calculation_error", symbol=symbol)

    try:
        result.atr = calculate_atr(df)
    except Exception:
        logger.exception("atr_calculation_error", symbol=symbol)

    try:
        result.macd = calculate_macd(
            df,
            fast=settings.macd_fast_period,
            slow=settings.macd_slow_period,
            signal=settings.macd_signal_period,
        )
    except Exception:
        logger.exception("macd_calculation_error", symbol=symbol)

    logger.debug(
        "analysis_complete",
        symbol=symbol,
        interval=interval,
        ema_trend=result.ema.get("trend"),
        rsi=result.rsi.get("rsi"),
        bb_position=result.bollinger.get("bb_position"),
    )

    return result
