"""Screener breakout potansiyeli skoru testleri."""

import pytest

from src.analysis.ta_engine import TAResult
from src.screener.analyzer import _calculate_breakout_score


class TestBreakoutScore:
    """Breakout potansiyeli skoru hesaplama testleri."""

    def _make_ta(
        self,
        bb_squeeze=False,
        volume_intensity=0.0,
        rsi=50,
        prev_rsi=50,
    ) -> TAResult:
        return TAResult(
            ema={"crossover": "none", "trend": "neutral"},
            rsi={"rsi": rsi, "zone": "neutral", "prev_rsi": prev_rsi},
            bollinger={"bb_position": "within", "bb_squeeze": bb_squeeze},
            volume={"is_spike": False, "volume_ratio": 1.0, "volume_intensity": volume_intensity},
            atr={"atr": 500, "atr_pct": 1.0},
            macd={"macd_crossover": "none"},
            current_price=50000.0,
            symbol="BTCUSDT",
            interval="15m",
        )

    def test_no_breakout_signals(self):
        """Hiçbir breakout sinyali yoksa skor 0 olmalı."""
        ta = self._make_ta()
        score = _calculate_breakout_score(ta)
        assert score == 0.0

    def test_squeeze_adds_score(self):
        """BB squeeze varsa 0.4 eklenmeli."""
        ta = self._make_ta(bb_squeeze=True)
        score = _calculate_breakout_score(ta)
        assert score == 0.4

    def test_volume_intensity_adds_score(self):
        """Volume intensity breakout skoruna katkı sağlamalı."""
        ta = self._make_ta(volume_intensity=1.0)
        score = _calculate_breakout_score(ta)
        assert score == 0.3  # 1.0 * 0.3

    def test_rsi_buildup_adds_score(self):
        """RSI 30-55 arası yükselen momentum skor eklemeli."""
        # RSI 45, prev 40 → buildup_strength = (45-30)/25 = 0.6
        ta = self._make_ta(rsi=45, prev_rsi=40)
        score = _calculate_breakout_score(ta)
        assert 0.15 < score < 0.25  # 0.6 * 0.3 = 0.18

    def test_rsi_not_rising_no_buildup(self):
        """RSI yükselmiyorsa buildup skoru olmamalı."""
        # RSI 45, prev 48 → düşüyor, buildup yok
        ta = self._make_ta(rsi=45, prev_rsi=48)
        score = _calculate_breakout_score(ta)
        assert score == 0.0

    def test_rsi_too_high_no_buildup(self):
        """RSI > 55 ise buildup olmamalı (zaten overbought bölgesine yakın)."""
        ta = self._make_ta(rsi=60, prev_rsi=55)
        score = _calculate_breakout_score(ta)
        assert score == 0.0

    def test_all_signals_combined(self):
        """Tüm sinyaller birlikte max skor vermeli."""
        ta = self._make_ta(
            bb_squeeze=True,
            volume_intensity=1.0,
            rsi=50,
            prev_rsi=40,
        )
        score = _calculate_breakout_score(ta)
        # 0.4 (squeeze) + 0.3 (volume) + (50-30)/25*0.3 = 0.4 + 0.3 + 0.24 = 0.94
        assert 0.9 < score <= 1.0

    def test_score_capped_at_1(self):
        """Skor 1.0'ı geçmemeli."""
        ta = self._make_ta(
            bb_squeeze=True,
            volume_intensity=1.0,
            rsi=55,
            prev_rsi=30,
        )
        score = _calculate_breakout_score(ta)
        assert score <= 1.0

    def test_rsi_none_no_crash(self):
        """RSI None olsa bile crash etmemeli."""
        ta = TAResult(
            rsi={"rsi": None, "prev_rsi": None},
            bollinger={"bb_squeeze": True},
            volume={"volume_intensity": 0.5},
        )
        score = _calculate_breakout_score(ta)
        assert score == 0.4 + 0.5 * 0.3  # squeeze + volume, RSI yok
