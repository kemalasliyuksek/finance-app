"""Teknik analiz indikatörleri - pandas-ta tabanlı.

Her fonksiyon pandas DataFrame alır, indikatör değerlerini döner.
Tüm fonksiyonlar bağımsız ve test edilebilir.
"""

from __future__ import annotations

import math

import pandas as pd
import pandas_ta as ta


def _safe_float(val) -> float | None:
    """NaN-safe float dönüşümü. NaN veya None ise None döner."""
    if val is None:
        return None
    try:
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return None
        return f
    except (ValueError, TypeError):
        return None


def calculate_ema(df: pd.DataFrame, fast_period: int = 9, slow_period: int = 21) -> dict:
    """EMA (Exponential Moving Average) hesapla.

    Returns:
        {
            "ema_fast": float,       # Son fast EMA değeri
            "ema_slow": float,       # Son slow EMA değeri
            "ema_diff": float,       # Fast - Slow farkı
            "crossover": str,        # "bullish" | "bearish" | "none"
            "trend": str,            # "up" | "down"
        }
    """
    ema_fast = ta.ema(df["close"], length=fast_period)
    ema_slow = ta.ema(df["close"], length=slow_period)

    if ema_fast is None or ema_slow is None or len(ema_fast) < 2:
        return {
            "ema_fast": None,
            "ema_slow": None,
            "ema_diff": None,
            "crossover": "none",
            "trend": "neutral",
        }

    fast_now = _safe_float(ema_fast.iloc[-1])
    fast_prev = _safe_float(ema_fast.iloc[-2])
    slow_now = _safe_float(ema_slow.iloc[-1])
    slow_prev = _safe_float(ema_slow.iloc[-2])

    if fast_now is None or fast_prev is None or slow_now is None or slow_prev is None:
        return {
            "ema_fast": None,
            "ema_slow": None,
            "ema_diff": None,
            "crossover": "none",
            "trend": "neutral",
        }

    # Crossover tespiti (strict karşılaştırma — eşitlik crossover değildir)
    crossover = "none"
    if fast_prev < slow_prev and fast_now > slow_now:
        crossover = "bullish"
    elif fast_prev > slow_prev and fast_now < slow_now:
        crossover = "bearish"

    trend = "up" if fast_now > slow_now else "down"

    return {
        "ema_fast": fast_now,
        "ema_slow": slow_now,
        "ema_diff": fast_now - slow_now,
        "crossover": crossover,
        "trend": trend,
    }


def calculate_rsi(df: pd.DataFrame, period: int = 14) -> dict:
    """RSI (Relative Strength Index) hesapla.

    Returns:
        {
            "rsi": float,            # Son RSI değeri (0-100)
            "zone": str,             # "overbought" | "oversold" | "neutral"
            "prev_rsi": float,       # Önceki RSI değeri
        }
    """
    rsi = ta.rsi(df["close"], length=period)

    if rsi is None or len(rsi) < 2:
        return {"rsi": None, "zone": "neutral", "prev_rsi": None}

    rsi_now = _safe_float(rsi.iloc[-1])
    rsi_prev = _safe_float(rsi.iloc[-2])

    if rsi_now is None:
        return {"rsi": None, "zone": "neutral", "prev_rsi": rsi_prev}

    if rsi_now >= 70:
        zone = "overbought"
    elif rsi_now <= 30:
        zone = "oversold"
    else:
        zone = "neutral"

    return {
        "rsi": rsi_now,
        "zone": zone,
        "prev_rsi": rsi_prev,
    }


def calculate_bollinger_bands(
    df: pd.DataFrame,
    period: int = 20,
    std_dev: float = 2.0,
    squeeze_lookback: int = 20,
    squeeze_percentile: float = 0.20,
) -> dict:
    """Bollinger Bands hesapla.

    Returns:
        {
            "bb_upper": float,               # Üst band
            "bb_middle": float,              # Orta band (SMA)
            "bb_lower": float,               # Alt band
            "bb_width": float,               # Band genişliği (%)
            "bb_position": str,              # "above_upper" | "below_lower" | "within"
            "price_vs_bb": float,            # Fiyatın band içindeki pozisyonu (0-1, 0=alt, 1=üst)
            "bb_squeeze": bool,              # Bandwidth tarihsel sıkışmada mı?
            "bb_bandwidth_percentile": float, # Bandwidth'in tarihsel percentile'i (0-1)
        }
    """
    bbands = ta.bbands(df["close"], length=period, std=std_dev)

    empty_result = {
        "bb_upper": None,
        "bb_middle": None,
        "bb_lower": None,
        "bb_width": None,
        "bb_position": "within",
        "price_vs_bb": 0.5,
        "bb_squeeze": False,
        "bb_bandwidth_percentile": 0.5,
    }

    if bbands is None or bbands.empty:
        return empty_result

    # pandas-ta kolon adları: BBL_20_2.0, BBM_20_2.0, BBU_20_2.0
    upper_col = [c for c in bbands.columns if c.startswith("BBU_")][0]
    middle_col = [c for c in bbands.columns if c.startswith("BBM_")][0]
    lower_col = [c for c in bbands.columns if c.startswith("BBL_")][0]

    upper = _safe_float(bbands[upper_col].iloc[-1])
    middle = _safe_float(bbands[middle_col].iloc[-1])
    lower = _safe_float(bbands[lower_col].iloc[-1])
    price = _safe_float(df["close"].iloc[-1])

    if upper is None or middle is None or lower is None or price is None:
        return empty_result

    # Band genişliği (%)
    bb_width = ((upper - lower) / middle) * 100 if middle > 0 else 0

    # Fiyat pozisyonu
    if price > upper:
        position = "above_upper"
    elif price < lower:
        position = "below_lower"
    else:
        position = "within"

    # Normalize pozisyon (0-1)
    band_range = upper - lower
    price_vs_bb = (price - lower) / band_range if band_range > 0 else 0.5

    # Squeeze detection: son N mumun bandwidth serisindeki percentile
    bb_squeeze = False
    bb_bandwidth_percentile = 0.5

    upper_series = bbands[upper_col]
    middle_series = bbands[middle_col]
    lower_series = bbands[lower_col]

    # Son squeeze_lookback mumun bandwidth'lerini hesapla
    lookback = min(squeeze_lookback, len(upper_series))
    if lookback >= 5 and middle is not None:
        width_series = []
        for i in range(-lookback, 0):
            u = _safe_float(upper_series.iloc[i])
            m = _safe_float(middle_series.iloc[i])
            l_val = _safe_float(lower_series.iloc[i])
            if u is not None and m is not None and l_val is not None and m > 0:
                width_series.append(((u - l_val) / m) * 100)

        if len(width_series) >= 5:
            current_width = width_series[-1]
            sorted_widths = sorted(width_series)
            rank = sum(1 for w in sorted_widths if w <= current_width)
            bb_bandwidth_percentile = rank / len(sorted_widths)
            bb_squeeze = bb_bandwidth_percentile <= squeeze_percentile

    return {
        "bb_upper": upper,
        "bb_middle": middle,
        "bb_lower": lower,
        "bb_width": bb_width,
        "bb_position": position,
        "price_vs_bb": max(0.0, min(1.0, price_vs_bb)),
        "bb_squeeze": bb_squeeze,
        "bb_bandwidth_percentile": round(bb_bandwidth_percentile, 4),
    }


def calculate_volume(
    df: pd.DataFrame,
    sma_period: int = 20,
    spike_mult: float = 1.5,
    max_ratio: float = 5.0,
) -> dict:
    """Volume analizi - spike tespiti ve kademeli yoğunluk.

    Returns:
        {
            "volume": float,          # Son hacim
            "volume_sma": float,      # Hacim SMA
            "volume_ratio": float,    # Mevcut / SMA oranı
            "is_spike": bool,         # Spike var mı? (geriye uyumlu)
            "volume_intensity": float, # Kademeli yoğunluk (0-1), ratio'ya orantılı
        }
    """
    vol = df["volume"].astype(float)
    vol_sma = ta.sma(vol, length=sma_period)

    if vol_sma is None or vol_sma.empty:
        return {
            "volume": float(vol.iloc[-1]) if len(vol) > 0 else 0,
            "volume_sma": None,
            "volume_ratio": 1.0,
            "is_spike": False,
            "volume_intensity": 0.0,
        }

    current_vol = _safe_float(vol.iloc[-1])
    sma_val = _safe_float(vol_sma.iloc[-1])

    if current_vol is None:
        return {
            "volume": 0,
            "volume_sma": None,
            "volume_ratio": 1.0,
            "is_spike": False,
            "volume_intensity": 0.0,
        }

    ratio = current_vol / sma_val if sma_val and sma_val > 0 else 1.0

    # Kademeli yoğunluk: ratio 1.0'dan başlar, max_ratio'da 1.0'a ulaşır
    if ratio <= 1.0 or max_ratio <= 1.0:
        intensity = 0.0
    else:
        intensity = min(1.0, max(0.0, (ratio - 1.0) / (max_ratio - 1.0)))

    return {
        "volume": current_vol,
        "volume_sma": sma_val,
        "volume_ratio": ratio,
        "is_spike": ratio >= spike_mult,
        "volume_intensity": round(intensity, 4),
    }


def calculate_atr(df: pd.DataFrame, period: int = 14) -> dict:
    """ATR (Average True Range) - stop-loss/take-profit hesaplama için.

    Returns:
        {
            "atr": float,            # Son ATR değeri
            "atr_pct": float,        # ATR / fiyat (%)
        }
    """
    atr = ta.atr(df["high"], df["low"], df["close"], length=period)

    if atr is None or atr.empty:
        return {"atr": None, "atr_pct": None}

    atr_val = _safe_float(atr.iloc[-1])
    price = _safe_float(df["close"].iloc[-1])

    if atr_val is None or price is None:
        return {"atr": None, "atr_pct": None}

    atr_pct = (atr_val / price) * 100 if price > 0 else 0

    return {
        "atr": atr_val,
        "atr_pct": atr_pct,
    }


def calculate_macd(
    df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9
) -> dict:
    """MACD (Moving Average Convergence Divergence).

    Returns:
        {
            "macd": float,           # MACD line
            "macd_signal": float,    # Signal line
            "macd_histogram": float, # Histogram
            "macd_crossover": str,   # "bullish" | "bearish" | "none"
        }
    """
    macd_df = ta.macd(df["close"], fast=fast, slow=slow, signal=signal)

    if macd_df is None or macd_df.empty:
        return {
            "macd": None,
            "macd_signal": None,
            "macd_histogram": None,
            "macd_crossover": "none",
        }

    # Explicit kolon adları (pandas-ta format: MACD_12_26_9, MACDs_12_26_9, MACDh_12_26_9)
    expected_macd = f"MACD_{fast}_{slow}_{signal}"
    expected_signal = f"MACDs_{fast}_{slow}_{signal}"
    expected_hist = f"MACDh_{fast}_{slow}_{signal}"

    if expected_macd in macd_df.columns:
        macd_col = expected_macd
        signal_col = expected_signal
        hist_col = expected_hist
    else:
        # Fallback: pattern-based arama
        try:
            macd_col = [c for c in macd_df.columns if c.startswith("MACD_") and not c.startswith("MACDs_") and not c.startswith("MACDh_")][0]
            signal_col = [c for c in macd_df.columns if c.startswith("MACDs_")][0]
            hist_col = [c for c in macd_df.columns if c.startswith("MACDh_")][0]
        except IndexError:
            return {
                "macd": None,
                "macd_signal": None,
                "macd_histogram": None,
                "macd_crossover": "none",
            }

    macd_now = _safe_float(macd_df[macd_col].iloc[-1])
    macd_prev = _safe_float(macd_df[macd_col].iloc[-2])
    signal_now = _safe_float(macd_df[signal_col].iloc[-1])
    signal_prev = _safe_float(macd_df[signal_col].iloc[-2])
    hist_now = _safe_float(macd_df[hist_col].iloc[-1])

    if macd_now is None or macd_prev is None or signal_now is None or signal_prev is None:
        return {
            "macd": macd_now,
            "macd_signal": signal_now,
            "macd_histogram": hist_now,
            "macd_crossover": "none",
        }

    # Strict crossover (eşitlik crossover değildir)
    crossover = "none"
    if macd_prev < signal_prev and macd_now > signal_now:
        crossover = "bullish"
    elif macd_prev > signal_prev and macd_now < signal_now:
        crossover = "bearish"

    return {
        "macd": macd_now,
        "macd_signal": signal_now,
        "macd_histogram": hist_now,
        "macd_crossover": crossover,
    }
