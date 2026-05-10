"""Strateji ve sinyal üretimi testleri."""

import pandas as pd
import pytest

from src.analysis.ta_engine import TAResult, run_analysis
from src.config import settings
from src.strategy.ema_crossover import EMACrossoverStrategy


class TestEMACrossoverStrategy:
    def setup_method(self):
        self.strategy = EMACrossoverStrategy()

    def test_name(self):
        assert self.strategy.name == "ema_crossover_v1"

    def test_no_signal_on_insufficient_data(self):
        ta = TAResult()
        signal = self.strategy.evaluate(ta)
        assert signal is None

    def test_low_confidence_signal_still_returned(self, sample_ohlcv_df: pd.DataFrame):
        """Strateji düşük güvenli sinyalleri de döner (filtreleme signal_generator'da)."""
        ta = run_analysis(sample_ohlcv_df, symbol="BTCUSDT", interval="15m")
        signal = self.strategy.evaluate(ta)
        # evaluate() gürültü filtresi (0.1) üstü tüm sinyalleri döner
        # Eşik filtrelemesi signal_generator'da yapılır
        if signal:
            assert float(signal.confidence) >= 0.1

    def test_signal_has_required_fields(self, trending_up_df: pd.DataFrame):
        """Sinyal üretildiğinde tüm gerekli alanlar dolu olmalı."""
        ta = run_analysis(trending_up_df, symbol="BTCUSDT", interval="15m")
        signal = self.strategy.evaluate(ta, sentiment_score=0.5)

        if signal:
            assert signal.symbol == "BTCUSDT"
            assert signal.side in ("BUY", "SELL")
            assert signal.strategy == "ema_crossover_v1"
            assert signal.entry_price > 0
            assert signal.stop_loss is not None
            assert signal.take_profit is not None
            assert signal.expires_at is not None
            assert signal.indicators is not None

    def test_sentiment_not_in_score(self, sample_ohlcv_df: pd.DataFrame):
        """Sentiment skoru confidence hesabını etkilememeli (devre dışı)."""
        ta = run_analysis(sample_ohlcv_df, symbol="BTCUSDT", interval="15m")

        signal_none = self.strategy.evaluate(ta, sentiment_score=None)
        signal_bull = self.strategy.evaluate(ta, sentiment_score=1.0)
        signal_bear = self.strategy.evaluate(ta, sentiment_score=-1.0)

        # Üçü de aynı confidence üretmeli (sentiment skorlamada yok)
        confs = set()
        for s in [signal_none, signal_bull, signal_bear]:
            confs.add(float(s.confidence) if s else None)
        assert len(confs) == 1

    def test_ema_score(self):
        """EMA skor hesaplaması doğru olmalı."""
        assert self.strategy._score_ema({"crossover": "bullish"}) == 1.0
        assert self.strategy._score_ema({"crossover": "bearish"}) == -1.0
        assert self.strategy._score_ema({"crossover": "none", "trend": "up"}) == settings.ema_trend_score
        assert self.strategy._score_ema({"crossover": "none", "trend": "down"}) == -settings.ema_trend_score

    def test_macd_score_crossover(self):
        """MACD crossover skorları doğru olmalı."""
        assert self.strategy._score_macd({"macd_crossover": "bullish"}) == 1.0
        assert self.strategy._score_macd({"macd_crossover": "bearish"}) == -1.0

    def test_macd_score_histogram(self):
        """MACD histogram skorları doğru olmalı."""
        assert self.strategy._score_macd({"macd_crossover": "none", "macd_histogram": 0.5}) == 0.5
        assert self.strategy._score_macd({"macd_crossover": "none", "macd_histogram": -0.3}) == -0.5
        assert self.strategy._score_macd({"macd_crossover": "none", "macd_histogram": 0}) == 0.0

    def test_macd_score_empty(self):
        """MACD verisi yoksa 0 dönmeli."""
        assert self.strategy._score_macd({}) == 0.0
        assert self.strategy._score_macd({"macd_crossover": "none", "macd_histogram": None}) == 0.0

    def test_rsi_score(self):
        """RSI skor hesaplaması doğru olmalı."""
        assert self.strategy._score_rsi({"rsi": 25}) == 1.0  # Oversold
        assert self.strategy._score_rsi({"rsi": 75}) == -1.0  # Overbought
        assert self.strategy._score_rsi({"rsi": 50}) == 0.0  # Neutral
        assert self.strategy._score_rsi({"rsi": 35}) == 0.5  # Hafif oversold

    def test_bb_score(self):
        """Bollinger skor hesaplaması doğru olmalı."""
        assert self.strategy._score_bollinger({"bb_position": "below_lower", "price_vs_bb": -0.1}) == 1.0
        assert self.strategy._score_bollinger({"bb_position": "above_upper", "price_vs_bb": 1.1}) == -1.0

    def test_volume_score_amplifies(self):
        """Volume yoğunluğu mevcut yönü orantılı güçlendirmeli."""
        # Güçlü yön (>= 0.5) + tam yoğunluk (1.0): tam amplification
        assert self.strategy._score_volume({"volume_intensity": 1.0}, 0.5) == 1.0
        assert self.strategy._score_volume({"volume_intensity": 1.0}, -0.5) == -1.0
        # Yoğunluk yok: 0
        assert self.strategy._score_volume({"volume_intensity": 0.0}, 0.5) == 0.0

    def test_volume_no_amplify_weak_signal(self):
        """Çok zayıf yön sinyali volume tarafından amplify edilmemeli."""
        assert self.strategy._score_volume({"volume_intensity": 1.0}, 0.01) == 0.0
        assert self.strategy._score_volume({"volume_intensity": 1.0}, -0.05) == 0.0
        assert self.strategy._score_volume({"volume_intensity": 1.0}, 0.14) == 0.0

    def test_volume_proportional_amplify(self):
        """Volume amplification yön gücü × yoğunluğa orantılı olmalı."""
        # 0.25 directional, 1.0 intensity → dir_mag = 0.25/0.5 = 0.5, result = 0.5 * 1.0
        result = self.strategy._score_volume({"volume_intensity": 1.0}, 0.25)
        assert 0.4 < result < 0.6  # ~0.5
        # 0.4 directional, 1.0 intensity → dir_mag = 0.4/0.5 = 0.8, result = 0.8 * 1.0
        result = self.strategy._score_volume({"volume_intensity": 1.0}, 0.4)
        assert 0.7 < result < 0.9  # ~0.8
        # 0.5 directional, 0.5 intensity → dir_mag = 1.0, result = 1.0 * 0.5 = 0.5
        result = self.strategy._score_volume({"volume_intensity": 0.5}, 0.5)
        assert 0.4 < result < 0.6  # ~0.5

    def test_bb_score_squeeze_amplifies(self):
        """BB squeeze + fiyat üst banda yakınsa skor yükselmeli."""
        # Squeeze + price_vs_bb > 0.85 → 0.8 dönmeli
        result = self.strategy._score_bollinger({
            "bb_position": "within", "price_vs_bb": 0.9, "bb_squeeze": True
        })
        assert result == 0.8

    def test_bb_score_squeeze_lower_bounce(self):
        """BB squeeze + fiyat alt banda yakınsa bounce potansiyeli yüksek."""
        result = self.strategy._score_bollinger({
            "bb_position": "within", "price_vs_bb": 0.1, "bb_squeeze": True
        })
        assert result == 0.8

    def test_bb_score_no_squeeze_unchanged(self):
        """Squeeze yoksa BB skoru normal kalmalı."""
        result = self.strategy._score_bollinger({
            "bb_position": "within", "price_vs_bb": 0.5, "bb_squeeze": False
        })
        assert result == 0.0

    def test_volume_intensity_scales_amplification(self):
        """Volume intensity arttıkça amplification güçlenmeli."""
        low = self.strategy._score_volume({"volume_intensity": 0.4}, 0.5)
        high = self.strategy._score_volume({"volume_intensity": 0.9}, 0.5)
        assert high > low

    def test_volume_below_min_intensity_no_amplify(self):
        """Min intensity altındaki hacim amplify etmemeli."""
        result = self.strategy._score_volume({"volume_intensity": 0.1}, 0.5)
        assert result == 0.0

    def test_confidence_reaches_threshold_with_macd(self):
        """EMA trend + MACD crossover birlikte 0.40 eşiğe ulaşmalı.

        Test environment-agnostic: eşik runtime'da 0.55 gibi daha yüksek
        bir değere ayarlanmış olsa bile strateji bileşenlerinin 0.40
        üretmesi gerektiğini doğrular.
        """
        ta = TAResult(
            ema={"ema_fast": 100, "ema_slow": 90, "crossover": "none", "trend": "up"},
            rsi={"rsi": 50, "zone": "neutral", "prev_rsi": 50},
            bollinger={"bb_position": "within", "price_vs_bb": 0.5},
            volume={"is_spike": False, "volume_ratio": 1.0},
            atr={"atr": 500, "atr_pct": 1.0},
            macd={"macd": 1, "macd_signal": 0, "macd_histogram": 0.5, "macd_crossover": "bullish"},
            current_price=50000.0,
            symbol="BTCUSDT",
            interval="15m",
        )
        signal = self.strategy.evaluate(ta)
        assert signal is not None
        # EMA trend (0.6*0.25=0.15) + MACD crossover (1.0*0.25=0.25) = 0.40
        assert float(signal.confidence) >= 0.40
