"""Teknik indikatör testleri."""

import pandas as pd
import pytest

from src.analysis.indicators import (
    calculate_atr,
    calculate_bollinger_bands,
    calculate_ema,
    calculate_macd,
    calculate_rsi,
    calculate_volume,
)


class TestEMA:
    def test_returns_values(self, sample_ohlcv_df: pd.DataFrame):
        result = calculate_ema(sample_ohlcv_df)
        assert result["ema_fast"] is not None
        assert result["ema_slow"] is not None
        assert result["trend"] in ("up", "down")
        assert result["crossover"] in ("bullish", "bearish", "none")

    def test_fast_responds_quicker(self, sample_ohlcv_df: pd.DataFrame):
        result = calculate_ema(sample_ohlcv_df, fast_period=5, slow_period=50)
        # Fast EMA daha güncel fiyata yakın olmalı
        current_price = float(sample_ohlcv_df["close"].iloc[-1])
        fast_diff = abs(result["ema_fast"] - current_price)
        slow_diff = abs(result["ema_slow"] - current_price)
        assert fast_diff <= slow_diff

    def test_empty_df(self):
        df = pd.DataFrame({"close": []})
        result = calculate_ema(df)
        assert result["ema_fast"] is None


class TestRSI:
    def test_returns_valid_range(self, sample_ohlcv_df: pd.DataFrame):
        result = calculate_rsi(sample_ohlcv_df)
        assert 0 <= result["rsi"] <= 100
        assert result["zone"] in ("overbought", "oversold", "neutral")

    def test_prev_rsi_exists(self, sample_ohlcv_df: pd.DataFrame):
        result = calculate_rsi(sample_ohlcv_df)
        assert result["prev_rsi"] is not None

    def test_empty_df(self):
        df = pd.DataFrame({"close": []})
        result = calculate_rsi(df)
        assert result["rsi"] is None


class TestBollingerBands:
    def test_band_ordering(self, sample_ohlcv_df: pd.DataFrame):
        result = calculate_bollinger_bands(sample_ohlcv_df)
        assert result["bb_lower"] < result["bb_middle"] < result["bb_upper"]

    def test_price_position_range(self, sample_ohlcv_df: pd.DataFrame):
        result = calculate_bollinger_bands(sample_ohlcv_df)
        assert 0 <= result["price_vs_bb"] <= 1

    def test_position_detection(self, sample_ohlcv_df: pd.DataFrame):
        result = calculate_bollinger_bands(sample_ohlcv_df)
        assert result["bb_position"] in ("above_upper", "below_lower", "within")


class TestVolume:
    def test_volume_ratio(self, sample_ohlcv_df: pd.DataFrame):
        result = calculate_volume(sample_ohlcv_df)
        assert result["volume_ratio"] > 0
        assert isinstance(result["is_spike"], bool)

    def test_spike_detection(self, sample_ohlcv_df: pd.DataFrame):
        # Spike = volume_ratio >= spike_mult
        result = calculate_volume(sample_ohlcv_df, spike_mult=0.1)  # Düşük eşik
        assert result["is_spike"] is True


class TestATR:
    def test_returns_positive(self, sample_ohlcv_df: pd.DataFrame):
        result = calculate_atr(sample_ohlcv_df)
        assert result["atr"] > 0
        assert result["atr_pct"] > 0


class TestMACD:
    def test_returns_values(self, sample_ohlcv_df: pd.DataFrame):
        result = calculate_macd(sample_ohlcv_df)
        assert result["macd"] is not None
        assert result["macd_signal"] is not None
        assert result["macd_histogram"] is not None
        assert result["macd_crossover"] in ("bullish", "bearish", "none")


# --- NaN Handling Testleri ---


class TestNaNHandling:
    """Tüm indikatörlerin NaN veriye karşı dayanıklılığı."""

    def test_ema_with_nan(self, nan_ohlcv_df: pd.DataFrame):
        result = calculate_ema(nan_ohlcv_df)
        # NaN durumunda None veya geçerli değer dönmeli, crash olmamalı
        if result["ema_fast"] is not None:
            assert isinstance(result["ema_fast"], float)
        assert result["crossover"] in ("bullish", "bearish", "none")
        assert result["trend"] in ("up", "down", "neutral")

    def test_rsi_with_nan(self, nan_ohlcv_df: pd.DataFrame):
        result = calculate_rsi(nan_ohlcv_df)
        if result["rsi"] is not None:
            assert 0 <= result["rsi"] <= 100
        assert result["zone"] in ("overbought", "oversold", "neutral")

    def test_bollinger_with_nan(self, nan_ohlcv_df: pd.DataFrame):
        result = calculate_bollinger_bands(nan_ohlcv_df)
        # NaN durumunda default dict dönmeli
        if result["bb_upper"] is not None:
            assert result["bb_lower"] < result["bb_upper"]
        assert result["bb_position"] in ("above_upper", "below_lower", "within")

    def test_volume_with_nan(self, nan_ohlcv_df: pd.DataFrame):
        result = calculate_volume(nan_ohlcv_df)
        assert isinstance(result["is_spike"], bool)
        assert result["volume_ratio"] >= 0

    def test_atr_with_nan(self, nan_ohlcv_df: pd.DataFrame):
        result = calculate_atr(nan_ohlcv_df)
        # NaN durumunda atr=None dönmeli
        if result["atr"] is not None:
            assert result["atr"] >= 0

    def test_macd_with_nan(self, nan_ohlcv_df: pd.DataFrame):
        result = calculate_macd(nan_ohlcv_df)
        assert result["macd_crossover"] in ("bullish", "bearish", "none")


class TestBBSqueeze:
    """Bollinger Bands squeeze detection testleri."""

    def test_squeeze_detected_narrow_bands(self, squeeze_df: pd.DataFrame):
        """Dar bandwidth durumunda bb_squeeze=True olmalı."""
        result = calculate_bollinger_bands(squeeze_df, squeeze_lookback=20, squeeze_percentile=0.30)
        assert result["bb_squeeze"] is True
        assert result["bb_bandwidth_percentile"] <= 0.30

    def test_no_squeeze_normal_data(self, sample_ohlcv_df: pd.DataFrame):
        """Normal volatilite verisinde squeeze olmayabilir."""
        result = calculate_bollinger_bands(sample_ohlcv_df, squeeze_lookback=20, squeeze_percentile=0.20)
        # Normal veride percentile 0-1 arası olmalı
        assert 0 <= result["bb_bandwidth_percentile"] <= 1

    def test_bandwidth_percentile_range(self, sample_ohlcv_df: pd.DataFrame):
        """Bandwidth percentile 0-1 arasında olmalı."""
        result = calculate_bollinger_bands(sample_ohlcv_df)
        assert 0 <= result["bb_bandwidth_percentile"] <= 1

    def test_squeeze_with_nan(self, nan_ohlcv_df: pd.DataFrame):
        """NaN veriyle squeeze hesaplaması crash etmemeli."""
        result = calculate_bollinger_bands(nan_ohlcv_df)
        assert isinstance(result["bb_squeeze"], bool)
        assert isinstance(result["bb_bandwidth_percentile"], float)


class TestVolumeIntensity:
    """Volume intensity (kademeli yoğunluk) testleri."""

    def test_intensity_proportional_to_ratio(self, sample_ohlcv_df: pd.DataFrame):
        """Yoğunluk ratio'ya orantılı olmalı."""
        result = calculate_volume(sample_ohlcv_df, max_ratio=5.0)
        assert 0 <= result["volume_intensity"] <= 1

    def test_intensity_zero_normal_volume(self):
        """Normal hacimde intensity 0 olmalı."""
        import numpy as np
        n = 50
        df = pd.DataFrame({
            "open": np.ones(n) * 100,
            "high": np.ones(n) * 101,
            "low": np.ones(n) * 99,
            "close": np.ones(n) * 100,
            "volume": np.ones(n) * 1000,  # Sabit hacim → ratio = 1.0
        })
        result = calculate_volume(df, max_ratio=5.0)
        assert result["volume_intensity"] == 0.0

    def test_intensity_high_spike(self):
        """Yüksek spike'da intensity yüksek olmalı."""
        import numpy as np
        n = 50
        volume = np.ones(n) * 500
        volume[-1] = 2500  # 5x spike
        df = pd.DataFrame({
            "open": np.ones(n) * 100,
            "high": np.ones(n) * 101,
            "low": np.ones(n) * 99,
            "close": np.ones(n) * 100,
            "volume": volume,
        })
        result = calculate_volume(df, max_ratio=5.0)
        assert result["volume_intensity"] > 0.7  # 5x / 5x max = ~1.0

    def test_intensity_capped_at_1(self):
        """Max 1.0 olmalı, ratio çok yüksek olsa bile."""
        import numpy as np
        n = 50
        volume = np.ones(n) * 100
        volume[-1] = 10000  # 100x spike
        df = pd.DataFrame({
            "open": np.ones(n) * 100,
            "high": np.ones(n) * 101,
            "low": np.ones(n) * 99,
            "close": np.ones(n) * 100,
            "volume": volume,
        })
        result = calculate_volume(df, max_ratio=5.0)
        assert result["volume_intensity"] == 1.0

    def test_intensity_with_nan(self, nan_ohlcv_df: pd.DataFrame):
        """NaN veriyle intensity crash etmemeli."""
        result = calculate_volume(nan_ohlcv_df)
        assert isinstance(result["volume_intensity"], float)


class TestStrictCrossover:
    """Strict crossover karşılaştırması: eşitlik crossover değildir."""

    def test_ema_no_crossover_when_equal(self, crossover_equal_df: pd.DataFrame):
        """EMA'lar eşit veya çok yakınken crossover olmamalı."""
        result = calculate_ema(crossover_equal_df)
        assert result["crossover"] == "none"

    def test_macd_no_crossover_when_equal(self, crossover_equal_df: pd.DataFrame):
        """MACD çizgileri eşitken crossover olmamalı."""
        result = calculate_macd(crossover_equal_df)
        assert result["macd_crossover"] == "none"
