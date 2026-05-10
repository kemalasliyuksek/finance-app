"""Config reload helper testleri — validate + apply + field listesi."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.config import settings
from src.core.config_reload import (
    apply_config_to_settings,
    validate_config_updates,
)
from src.db.repositories.app_config_repo import APP_CONFIG_FIELDS


class TestValidateConfigUpdates:
    def test_valid_single_field(self):
        """Tek alan geçerliyse validate başarılı olmalı."""
        result = validate_config_updates({"risk_per_trade_pct": 0.03})
        assert result.risk_per_trade_pct == 0.03

    def test_valid_multiple_fields(self):
        """Birden fazla alan geçerliyse validate başarılı olmalı."""
        result = validate_config_updates(
            {
                "min_signal_confidence": 0.55,
                "max_concurrent_positions": 3,
                "cooldown_seconds": 600,
            }
        )
        assert result.min_signal_confidence == 0.55
        assert result.max_concurrent_positions == 3

    def test_strategy_weights_sum_not_one_rejected(self):
        """Strateji ağırlıkları toplamı 1.0 değilse ValidationError."""
        with pytest.raises(ValidationError, match="Strateji ağırlıkları"):
            validate_config_updates(
                {
                    "strategy_w_ema": 0.8,
                    "strategy_w_macd": 0.8,
                }
            )

    def test_strategy_weights_rebalanced_accepted(self):
        """Tüm ağırlıkları 1.0 olacak şekilde gönderirsen geçerli."""
        result = validate_config_updates(
            {
                "strategy_w_ema": 0.30,
                "strategy_w_macd": 0.30,
                "strategy_w_rsi": 0.20,
                "strategy_w_bb": 0.10,
                "strategy_w_volume": 0.10,
            }
        )
        assert result.strategy_w_ema == 0.30

    def test_max_sl_less_than_min_sl_rejected(self):
        """MAX_SL_PCT <= MIN_SL_PCT ise ValidationError."""
        with pytest.raises(ValidationError, match="MAX_SL_PCT"):
            validate_config_updates(
                {"min_sl_pct": 0.05, "max_sl_pct": 0.02}
            )

    def test_tp_multiplier_less_than_sl_rejected(self):
        """ATR_TP_MULTIPLIER <= ATR_SL_MULTIPLIER ise ValidationError (R:R < 1)."""
        with pytest.raises(ValidationError, match="ATR_TP_MULTIPLIER"):
            validate_config_updates(
                {"atr_sl_multiplier": 3.0, "atr_tp_multiplier": 2.0}
            )

    def test_validate_does_not_mutate_settings(self):
        """Validate sadece doğrular, settings singleton'ına dokunmaz."""
        original = settings.risk_per_trade_pct
        try:
            validate_config_updates({"risk_per_trade_pct": 0.099})
        except ValidationError:
            pass
        assert settings.risk_per_trade_pct == original


class TestApplyConfigToSettings:
    @pytest.mark.asyncio
    async def test_apply_updates_settings(self):
        """Geçerli değerler settings singleton'ına uygulanır."""
        original = settings.cooldown_seconds
        try:
            await apply_config_to_settings({"cooldown_seconds": 777})
            assert settings.cooldown_seconds == 777
        finally:
            settings.cooldown_seconds = original

    @pytest.mark.asyncio
    async def test_apply_empty_is_noop(self):
        """Boş dict hiçbir şey yapmamalı."""
        original = settings.risk_per_trade_pct
        await apply_config_to_settings({})
        assert settings.risk_per_trade_pct == original

    @pytest.mark.asyncio
    async def test_apply_invalid_raises(self):
        """Geçersiz kombinasyon ValidationError fırlatır, settings değişmez."""
        original_min = settings.min_sl_pct
        original_max = settings.max_sl_pct
        with pytest.raises(ValidationError):
            await apply_config_to_settings(
                {"min_sl_pct": 0.08, "max_sl_pct": 0.02}
            )
        assert settings.min_sl_pct == original_min
        assert settings.max_sl_pct == original_max


class TestAppConfigFields:
    def test_fields_count_is_27(self):
        """27 parametrenin tam listesi merkezi olarak tanımlı olmalı."""
        assert len(APP_CONFIG_FIELDS) == 27

    def test_all_fields_exist_on_settings(self):
        """APP_CONFIG_FIELDS içindeki her alan settings'te bulunmalı."""
        for field in APP_CONFIG_FIELDS:
            assert hasattr(settings, field), f"settings'te eksik alan: {field}"

    def test_trading_mode_is_in_fields(self):
        """trading_mode listede olmalı (kullanıcı özel olarak istedi)."""
        assert "trading_mode" in APP_CONFIG_FIELDS

    def test_no_duplicate_fields(self):
        """Aynı alan iki kere eklenmemiş olmalı."""
        assert len(APP_CONFIG_FIELDS) == len(set(APP_CONFIG_FIELDS))
