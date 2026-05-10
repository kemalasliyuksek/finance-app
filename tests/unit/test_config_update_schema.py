"""TradingConfigUpdate pydantic schema testleri."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.api.endpoints.config_api import TradingConfigUpdate


class TestTradingConfigUpdate:
    def test_all_fields_optional(self):
        """Boş body geçerli olmalı (endpoint zaten 400 döner)."""
        body = TradingConfigUpdate()
        assert body.model_dump(exclude_unset=True) == {}

    def test_extra_fields_forbidden(self):
        """Bilinmeyen alanlar 422 (extra='forbid')."""
        with pytest.raises(ValidationError):
            TradingConfigUpdate(unknown_field=1.0)

    def test_risk_per_trade_pct_bounds(self):
        TradingConfigUpdate(risk_per_trade_pct=0.03)
        with pytest.raises(ValidationError):
            TradingConfigUpdate(risk_per_trade_pct=0.2)  # > 0.10
        with pytest.raises(ValidationError):
            TradingConfigUpdate(risk_per_trade_pct=0.0)  # < 0.001

    def test_max_concurrent_positions_bounds(self):
        TradingConfigUpdate(max_concurrent_positions=3)
        with pytest.raises(ValidationError):
            TradingConfigUpdate(max_concurrent_positions=20)
        with pytest.raises(ValidationError):
            TradingConfigUpdate(max_concurrent_positions=0)

    def test_trading_mode_literal(self):
        TradingConfigUpdate(trading_mode="semi_auto")
        TradingConfigUpdate(trading_mode="full_auto")
        with pytest.raises(ValidationError):
            TradingConfigUpdate(trading_mode="manual")

    def test_min_signal_confidence_bounds(self):
        TradingConfigUpdate(min_signal_confidence=0.55)
        with pytest.raises(ValidationError):
            TradingConfigUpdate(min_signal_confidence=0.05)
        with pytest.raises(ValidationError):
            TradingConfigUpdate(min_signal_confidence=1.5)

    def test_sl_multiplier_bounds(self):
        TradingConfigUpdate(atr_sl_multiplier=2.0)
        with pytest.raises(ValidationError):
            TradingConfigUpdate(atr_sl_multiplier=0.1)
        with pytest.raises(ValidationError):
            TradingConfigUpdate(atr_sl_multiplier=15)

    def test_partial_update_only_sent_fields(self):
        """Sadece gönderilen alanlar model_dump(exclude_unset) içinde olmalı."""
        body = TradingConfigUpdate(
            min_signal_confidence=0.55, cooldown_seconds=600
        )
        sent = body.model_dump(exclude_unset=True)
        assert set(sent.keys()) == {"min_signal_confidence", "cooldown_seconds"}

    def test_screener_volume_bounds(self):
        TradingConfigUpdate(screener_min_volume_usdt=1_000_000)
        with pytest.raises(ValidationError):
            TradingConfigUpdate(screener_min_volume_usdt=1_000)  # < 10k
        with pytest.raises(ValidationError):
            TradingConfigUpdate(screener_min_volume_usdt=1_000_000_000)  # > 100M
