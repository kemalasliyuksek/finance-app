"""Test fixtures."""

import math

import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def sample_ohlcv_df() -> pd.DataFrame:
    """100 mumlu sentetik OHLCV veri seti."""
    np.random.seed(42)
    n = 100
    close = 65000 + np.cumsum(np.random.randn(n) * 100)
    high = close + np.abs(np.random.randn(n)) * 200
    low = close - np.abs(np.random.randn(n)) * 200
    open_p = close + np.random.randn(n) * 50
    volume = np.abs(np.random.randn(n)) * 1000 + 500

    dates = pd.date_range("2026-01-01", periods=n, freq="15min")
    return pd.DataFrame(
        {"open": open_p, "high": high, "low": low, "close": close, "volume": volume},
        index=dates,
    )


@pytest.fixture
def trending_up_df() -> pd.DataFrame:
    """Güçlü yükselen trend verisi - sinyal üretimi için."""
    np.random.seed(123)
    n = 100
    close = 60000 + np.arange(n) * 50 + np.random.randn(n) * 30
    high = close + np.abs(np.random.randn(n)) * 100
    low = close - np.abs(np.random.randn(n)) * 100
    open_p = close - 20
    volume = np.ones(n) * 500
    # Son 5 mumda volume spike
    volume[-5:] = 2000

    dates = pd.date_range("2026-01-01", periods=n, freq="15min")
    return pd.DataFrame(
        {"open": open_p, "high": high, "low": low, "close": close, "volume": volume},
        index=dates,
    )


@pytest.fixture
def nan_ohlcv_df() -> pd.DataFrame:
    """Son değerleri NaN olan OHLCV veri seti — NaN handling testi için."""
    np.random.seed(42)
    n = 50
    close = 65000 + np.cumsum(np.random.randn(n) * 100)
    high = close + np.abs(np.random.randn(n)) * 200
    low = close - np.abs(np.random.randn(n)) * 200
    open_p = close + np.random.randn(n) * 50
    volume = np.abs(np.random.randn(n)) * 1000 + 500

    # Son 2 mum NaN
    close[-2:] = math.nan
    high[-2:] = math.nan
    low[-2:] = math.nan
    open_p[-2:] = math.nan
    volume[-2:] = math.nan

    dates = pd.date_range("2026-01-01", periods=n, freq="15min")
    return pd.DataFrame(
        {"open": open_p, "high": high, "low": low, "close": close, "volume": volume},
        index=dates,
    )


@pytest.fixture
def squeeze_df() -> pd.DataFrame:
    """BB bandları sıkışmış veri seti — squeeze testi için.

    İlk 80 mum normal volatilite, son 20 mum çok düşük volatilite (sıkışma).
    """
    np.random.seed(55)
    n = 100
    # İlk 80 mum: normal volatilite
    close_start = 50000 + np.cumsum(np.random.randn(80) * 200)
    # Son 20 mum: çok dar hareket (squeeze)
    last_price = close_start[-1]
    close_end = last_price + np.random.randn(20) * 5  # Çok az hareket

    close = np.concatenate([close_start, close_end])
    high = close + np.abs(np.random.randn(n)) * 50
    low = close - np.abs(np.random.randn(n)) * 50
    # Son 20'de high/low da çok dar
    high[-20:] = close[-20:] + 3
    low[-20:] = close[-20:] - 3
    open_p = close + np.random.randn(n) * 10

    volume = np.ones(n) * 1000
    dates = pd.date_range("2026-01-01", periods=n, freq="15min")
    return pd.DataFrame(
        {"open": open_p, "high": high, "low": low, "close": close, "volume": volume},
        index=dates,
    )


@pytest.fixture
def volume_breakout_df() -> pd.DataFrame:
    """Son mumlarda ani volume spike olan veri seti — volume breakout testi için."""
    np.random.seed(77)
    n = 100
    close = 50000 + np.cumsum(np.random.randn(n) * 100)
    high = close + np.abs(np.random.randn(n)) * 100
    low = close - np.abs(np.random.randn(n)) * 100
    open_p = close + np.random.randn(n) * 30

    # Normal hacim, son 3 mumda 5x spike
    volume = np.ones(n) * 500
    volume[-3:] = 2500  # 5x normal
    volume[-1] = 5000   # 10x normal

    dates = pd.date_range("2026-01-01", periods=n, freq="15min")
    return pd.DataFrame(
        {"open": open_p, "high": high, "low": low, "close": close, "volume": volume},
        index=dates,
    )


@pytest.fixture
def crossover_equal_df() -> pd.DataFrame:
    """EMA'lar eşit geçen veri seti — strict crossover testi için.

    EMA9 ve EMA21 son 2 mumda birbirine çok yakın ama eşit.
    """
    np.random.seed(99)
    n = 100
    # Düz trend (EMA'lar yakınsar)
    close = np.full(n, 50000.0)
    # Son mumlarda minimal hareket — crossover yok
    close[-1] = 50000.01
    close[-2] = 50000.0

    high = close + 10
    low = close - 10
    open_p = close

    volume = np.ones(n) * 1000

    dates = pd.date_range("2026-01-01", periods=n, freq="15min")
    return pd.DataFrame(
        {"open": open_p, "high": high, "low": low, "close": close, "volume": volume},
        index=dates,
    )
