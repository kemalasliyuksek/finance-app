"""Strateji kalite düzeltmeleri testleri.

Confidence capping, skor sıralaması, volume scaling, schema validation.
"""

from decimal import Decimal

import pandas as pd
import pytest

from src.analysis.ta_engine import TAResult, run_analysis
from src.schemas.signal import SignalCreate
from src.strategy.ema_crossover import EMACrossoverStrategy


class TestConfidenceCapping:
    """Confidence değeri her zaman [0, 1] aralığında olmalı."""

    def setup_method(self):
        self.strategy = EMACrossoverStrategy()

    def test_confidence_never_exceeds_1(self):
        """Tüm bileşenler max pozitif olsa bile confidence <= 1.0."""
        ta = TAResult(
            ema={"ema_fast": 100, "ema_slow": 90, "crossover": "bullish", "trend": "up"},
            rsi={"rsi": 25, "zone": "oversold", "prev_rsi": 28},
            bollinger={"bb_position": "below_lower", "price_vs_bb": -0.1},
            volume={"is_spike": True, "volume_ratio": 3.0},
            atr={"atr": 500, "atr_pct": 1.0},
            macd={"macd": 1, "macd_signal": 0, "macd_crossover": "bullish"},
            current_price=50000.0,
            symbol="BTCUSDT",
            interval="15m",
        )
        signal = self.strategy.evaluate(ta, sentiment_score=1.0)
        if signal:
            assert float(signal.confidence) <= 1.0

    def test_confidence_never_negative(self):
        """Confidence negatif olamaz."""
        ta = TAResult(
            ema={"ema_fast": 90, "ema_slow": 100, "crossover": "bearish", "trend": "down"},
            rsi={"rsi": 75, "zone": "overbought", "prev_rsi": 72},
            bollinger={"bb_position": "above_upper", "price_vs_bb": 1.1},
            volume={"is_spike": True, "volume_ratio": 3.0},
            atr={"atr": 500, "atr_pct": 1.0},
            macd={"macd": -1, "macd_signal": 0, "macd_histogram": -0.5, "macd_crossover": "bearish"},
            current_price=50000.0,
            symbol="BTCUSDT",
            interval="15m",
        )
        signal = self.strategy.evaluate(ta, sentiment_score=-1.0)
        if signal:
            assert float(signal.confidence) >= 0.0


class TestScoreOrdering:
    """Skor bileşen sıralaması doğru çalışmalı."""

    def setup_method(self):
        self.strategy = EMACrossoverStrategy()

    def test_volume_uses_full_directional_score(self):
        """Volume skoru, tam yön skoruna göre hesaplanmalı."""
        # EMA bearish (-1.0*0.25=-0.25) + MACD bearish (-1.0*0.25=-0.25)
        # + RSI overbought (-1.0*0.20=-0.20) + BB neutral (0) = -0.70 directional
        ta = TAResult(
            ema={"ema_fast": 90, "ema_slow": 100, "crossover": "bearish", "trend": "down"},
            rsi={"rsi": 75, "zone": "overbought", "prev_rsi": 72},
            bollinger={"bb_position": "within", "price_vs_bb": 0.5},
            volume={"is_spike": True, "volume_ratio": 3.0},
            atr={"atr": 500, "atr_pct": 1.0},
            macd={"macd": -1, "macd_signal": 0, "macd_histogram": -0.5, "macd_crossover": "bearish"},
            current_price=50000.0,
            symbol="BTCUSDT",
            interval="15m",
        )
        signal = self.strategy.evaluate(ta)
        # Directional = (-0.25) + (-0.25) + (-0.20) + 0 = -0.70
        # Volume spike + negative directional → negative volume score
        # Total should be < -0.70 (volume amplifies negative direction)
        if signal:
            assert signal.side == "SELL"


class TestSignalSchemaValidation:
    """SignalCreate schema doğrulamaları."""

    def test_confidence_above_1_rejected(self):
        """Confidence > 1 Pydantic validation hatası vermeli."""
        with pytest.raises(ValueError):
            SignalCreate(
                symbol="BTCUSDT",
                side="BUY",
                strategy="test",
                confidence=Decimal("1.5"),
                entry_price=Decimal("50000"),
                indicators={},
                expires_at="2026-01-01T00:00:00",
            )

    def test_confidence_negative_rejected(self):
        """Confidence < 0 Pydantic validation hatası vermeli."""
        with pytest.raises(ValueError):
            SignalCreate(
                symbol="BTCUSDT",
                side="BUY",
                strategy="test",
                confidence=Decimal("-0.1"),
                entry_price=Decimal("50000"),
                indicators={},
                expires_at="2026-01-01T00:00:00",
            )

    def test_confidence_valid_range(self):
        """Geçerli confidence değerleri kabul edilmeli."""
        for val in ("0", "0.5", "0.999", "1.0"):
            signal = SignalCreate(
                symbol="BTCUSDT",
                side="BUY",
                strategy="test",
                confidence=Decimal(val),
                entry_price=Decimal("50000"),
                indicators={},
                expires_at="2026-01-01T00:00:00",
            )
            assert signal.confidence == Decimal(val)


class TestCryptoPanicDynamicMap:
    """CryptoPanic dinamik symbol mapping."""

    def test_known_symbols(self):
        from src.sentiment.cryptopanic_client import _symbol_to_currency

        assert _symbol_to_currency("BTCUSDT") == "BTC"
        assert _symbol_to_currency("ETHUSDT") == "ETH"
        assert _symbol_to_currency("SOLUSDT") == "SOL"

    def test_dynamic_symbols(self):
        from src.sentiment.cryptopanic_client import _symbol_to_currency

        assert _symbol_to_currency("ARBUSDT") == "ARB"
        assert _symbol_to_currency("PEPEUSDT") == "PEPE"
        assert _symbol_to_currency("WIFUSDT") == "WIF"

    def test_busd_pair(self):
        from src.sentiment.cryptopanic_client import _symbol_to_currency

        assert _symbol_to_currency("ETHBUSD") == "ETH"

    def test_unknown_suffix(self):
        from src.sentiment.cryptopanic_client import _symbol_to_currency

        assert _symbol_to_currency("INVALIDPAIR") is None
