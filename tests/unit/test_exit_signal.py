"""Çıkış sinyali testleri."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from src.strategy.ema_crossover import EMACrossoverStrategy


@dataclass
class MockTrade:
    symbol: str = "BTCUSDT"
    side: str = "BUY"
    entry_price: Decimal = Decimal("50000")
    stop_loss: Decimal = Decimal("48000")
    take_profit: Decimal = Decimal("54000")


@dataclass
class MockTAResult:
    ema: dict
    rsi: dict
    bollinger: dict
    volume: dict
    atr: dict
    macd: dict
    current_price: float | None
    symbol: str = "BTCUSDT"
    interval: str = "15m"
    recent_high: float | None = None
    recent_low: float | None = None

    def to_dict(self):
        return {}


class TestExitSignal:
    def setup_method(self):
        self.strategy = EMACrossoverStrategy()

    def _make_ta(self, price, ema_crossover="none", rsi=50, macd_crossover="none"):
        return MockTAResult(
            ema={"crossover": ema_crossover, "trend": "neutral"},
            rsi={"rsi": rsi, "zone": "neutral"},
            bollinger={"bb_position": 0.5},
            volume={"is_spike": False, "volume_ratio": 1.0},
            atr={"atr": 500},
            macd={"macd_crossover": macd_crossover},
            current_price=price,
        )

    def test_stop_loss_hit_long(self):
        """Long pozisyonda fiyat stop-loss'a düştüğünde çıkış."""
        ta = self._make_ta(price=47500)
        trade = MockTrade(side="BUY", stop_loss=Decimal("48000"))

        exit_signal = self.strategy.evaluate_exit(ta, trade)

        assert exit_signal is not None
        assert exit_signal.reason == "stop_loss"
        assert exit_signal.side == "SELL"
        assert exit_signal.confidence == 1.0

    def test_take_profit_hit_long(self):
        """Long pozisyonda fiyat take-profit'e ulaştığında çıkış."""
        ta = self._make_ta(price=55000)
        trade = MockTrade(side="BUY", take_profit=Decimal("54000"))

        exit_signal = self.strategy.evaluate_exit(ta, trade)

        assert exit_signal is not None
        assert exit_signal.reason == "take_profit"
        assert exit_signal.side == "SELL"

    def test_ema_reverse_with_profit_exits(self):
        """EMA ters crossover + %2 kârdaysa çıkış (kâr koruma)."""
        # %4 kâr (50000 → 52000)
        ta = self._make_ta(price=52000, ema_crossover="bearish")
        trade = MockTrade(side="BUY", entry_price=Decimal("50000"))

        exit_signal = self.strategy.evaluate_exit(ta, trade)

        assert exit_signal is not None
        assert exit_signal.reason == "profit_protect"
        assert exit_signal.confidence == 0.85

    def test_ema_reverse_without_profit_no_exit(self):
        """EMA ters crossover ama kâr yok → çıkış yok (erken satış engeli)."""
        # %0 kâr/zarar (50000 → 50000)
        ta = self._make_ta(price=50000, ema_crossover="bearish")
        trade = MockTrade(side="BUY", entry_price=Decimal("50000"))

        exit_signal = self.strategy.evaluate_exit(ta, trade)

        assert exit_signal is None

    def test_rsi_overbought_with_profit_exits(self):
        """RSI > 80 ve kârdaysa çıkış."""
        # %4 kâr + RSI 85
        ta = self._make_ta(price=52000, rsi=85)
        trade = MockTrade(side="BUY", entry_price=Decimal("50000"))

        exit_signal = self.strategy.evaluate_exit(ta, trade)

        assert exit_signal is not None
        assert exit_signal.reason == "rsi_overbought_profit"

    def test_rsi_overbought_no_profit_no_exit(self):
        """RSI > 80 ama kâr yok → çıkış yok."""
        ta = self._make_ta(price=50000, rsi=85)
        trade = MockTrade(side="BUY", entry_price=Decimal("50000"))

        exit_signal = self.strategy.evaluate_exit(ta, trade)

        assert exit_signal is None

    def test_trend_loss_exit(self):
        """-%3 zarar + EMA ve MACD bearish → zarar kes."""
        # -%4 zarar (50000 → 48000)
        ta = self._make_ta(price=48000, ema_crossover="bearish", macd_crossover="bearish")
        trade = MockTrade(side="BUY", entry_price=Decimal("50000"), stop_loss=Decimal("46000"))

        exit_signal = self.strategy.evaluate_exit(ta, trade)

        assert exit_signal is not None
        assert exit_signal.reason == "stop_trend_loss"

    def test_small_loss_no_exit(self):
        """-%1 zarar + EMA bearish → çıkış yok (henüz erken)."""
        ta = self._make_ta(price=49500, ema_crossover="bearish", macd_crossover="bearish")
        trade = MockTrade(side="BUY", entry_price=Decimal("50000"), stop_loss=Decimal("46000"))

        exit_signal = self.strategy.evaluate_exit(ta, trade)

        assert exit_signal is None

    def test_no_exit_normal_conditions(self):
        """Normal koşullarda çıkış sinyali yok."""
        ta = self._make_ta(price=51000, rsi=55)
        trade = MockTrade(side="BUY")

        exit_signal = self.strategy.evaluate_exit(ta, trade)

        assert exit_signal is None

    def test_stop_loss_hit_short(self):
        """Short pozisyonda fiyat stop-loss'a çıktığında çıkış."""
        ta = self._make_ta(price=53000)
        trade = MockTrade(side="SELL", stop_loss=Decimal("52000"))

        exit_signal = self.strategy.evaluate_exit(ta, trade)

        assert exit_signal is not None
        assert exit_signal.reason == "stop_loss"
        assert exit_signal.side == "BUY"

    def test_no_price_no_exit(self):
        """Fiyat yoksa çıkış sinyali üretilmez."""
        ta = self._make_ta(price=None)
        trade = MockTrade()

        exit_signal = self.strategy.evaluate_exit(ta, trade)

        assert exit_signal is None


class TestTrailingStop:
    """Trailing stop testleri."""

    def setup_method(self):
        self.strategy = EMACrossoverStrategy()

    def _make_ta(self, price, recent_high=None, recent_low=None):
        return MockTAResult(
            ema={"crossover": "none", "trend": "neutral"},
            rsi={"rsi": 50, "zone": "neutral"},
            bollinger={"bb_position": "within"},
            volume={"is_spike": False, "volume_ratio": 1.0},
            atr={"atr": 500},
            macd={"macd_crossover": "none"},
            current_price=price,
            recent_high=recent_high,
            recent_low=recent_low,
        )

    def test_trailing_triggers_after_profit(self):
        """Kâr eşiğinin üstünde ve zirveden düşüş varsa trailing tetiklenmeli."""
        # Entry: 50000, current: 52000 (%4 kâr), recent_high: 53500
        # Zirveden düşüş: 53500 → 52000 = %2.8 > trail_pct(%2)
        ta = self._make_ta(price=52000, recent_high=53500)
        trade = MockTrade(side="BUY", entry_price=Decimal("50000"), stop_loss=Decimal("48000"))

        exit_signal = self.strategy.evaluate_exit(ta, trade)

        assert exit_signal is not None
        assert exit_signal.reason == "trailing_stop"
        assert exit_signal.confidence == 0.95

    def test_trailing_not_active_below_threshold(self):
        """Kâr aktivasyon eşiğinin altındaysa trailing tetiklenmemeli."""
        # Entry: 50000, current: 50500 (%1 kâr < %2 aktivasyon)
        ta = self._make_ta(price=50500, recent_high=51000)
        trade = MockTrade(side="BUY", entry_price=Decimal("50000"), stop_loss=Decimal("48000"))

        exit_signal = self.strategy.evaluate_exit(ta, trade)

        assert exit_signal is None

    def test_trailing_not_triggered_price_near_high(self):
        """Fiyat zirveye yakınsa trailing tetiklenmemeli."""
        # Entry: 50000, current: 52000 (%4 kâr), recent_high: 52100
        # Zirveden düşüş: 52100 → 52000 = %0.2 < trail_pct(%2)
        ta = self._make_ta(price=52000, recent_high=52100)
        trade = MockTrade(side="BUY", entry_price=Decimal("50000"), stop_loss=Decimal("48000"))

        exit_signal = self.strategy.evaluate_exit(ta, trade)

        assert exit_signal is None

    def test_trailing_short_position(self):
        """Short pozisyonda trailing stop çalışmalı."""
        # Entry: 50000, current: 48000 (%4 kâr short), recent_low: 47000
        # Dip'ten yükseliş: 47000 → 48000 = %2.1 > trail_pct(%2)
        ta = self._make_ta(price=48000, recent_high=50500, recent_low=47000)
        trade = MockTrade(
            side="SELL",
            entry_price=Decimal("50000"),
            stop_loss=Decimal("52000"),
            take_profit=Decimal("46000"),  # Short TP: entry altı
        )

        exit_signal = self.strategy.evaluate_exit(ta, trade)

        assert exit_signal is not None
        assert exit_signal.reason == "trailing_stop"


class TestTimeBasedExit:
    """Zaman bazlı çıkış testleri."""

    def setup_method(self):
        self.strategy = EMACrossoverStrategy()

    def _make_ta(self, price):
        return MockTAResult(
            ema={"crossover": "none", "trend": "neutral"},
            rsi={"rsi": 50, "zone": "neutral"},
            bollinger={"bb_position": "within"},
            volume={"is_spike": False, "volume_ratio": 1.0},
            atr={"atr": 500},
            macd={"macd_crossover": "none"},
            current_price=price,
        )

    def test_time_exit_no_profit(self):
        """Süre aşımı + kâr yetersiz → çıkış."""
        ta = self._make_ta(price=50050)  # %0.1 kâr < %0.5 eşik
        trade = MockTrade(
            side="BUY",
            entry_price=Decimal("50000"),
            stop_loss=Decimal("48000"),
        )
        # 5 saat önce açılmış (> 4 saat max)
        trade.opened_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=5)

        exit_signal = self.strategy.evaluate_exit(ta, trade)

        assert exit_signal is not None
        assert exit_signal.reason == "time_exit"
        assert exit_signal.confidence == 0.7

    def test_time_exit_with_profit_stays(self):
        """Süre aşımı ama kâr yeterli → çıkış yok."""
        ta = self._make_ta(price=50500)  # %1 kâr > %0.5 eşik
        trade = MockTrade(
            side="BUY",
            entry_price=Decimal("50000"),
            stop_loss=Decimal("48000"),
        )
        trade.opened_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=5)

        exit_signal = self.strategy.evaluate_exit(ta, trade)

        assert exit_signal is None

    def test_time_exit_not_triggered_early(self):
        """Süre aşılmamış → çıkış yok."""
        ta = self._make_ta(price=50050)  # Düşük kâr
        trade = MockTrade(
            side="BUY",
            entry_price=Decimal("50000"),
            stop_loss=Decimal("48000"),
        )
        trade.opened_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=2)  # < 4 saat

        exit_signal = self.strategy.evaluate_exit(ta, trade)

        assert exit_signal is None
