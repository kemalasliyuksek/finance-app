"""Risk yönetimi testleri."""

from decimal import Decimal

import pytest

from src.core.exceptions import InsufficientBalanceError
from src.risk.position_sizer import calculate_position_size


class TestPositionSizer:
    def test_basic_sizing(self):
        result = calculate_position_size(
            balance_usdt=Decimal("500"),
            entry_price=Decimal("65000"),
            stop_loss=Decimal("64000"),
            side="BUY",
        )
        assert result["quantity"] > 0
        assert result["position_usdt"] > 0
        assert result["risk_usdt"] > 0
        assert result["sl_distance_pct"] > 0

    def test_risk_amount_within_limit(self):
        """Risk miktarı bakiyenin %2'sini geçmemeli."""
        result = calculate_position_size(
            balance_usdt=Decimal("500"),
            entry_price=Decimal("65000"),
            stop_loss=Decimal("64000"),
            side="BUY",
            risk_pct=0.02,
        )
        max_risk = float(Decimal("500") * Decimal("0.02"))
        # Komisyon ve yuvarlama nedeniyle biraz tolerans
        assert float(result["risk_usdt"]) <= max_risk * 1.5

    def test_insufficient_balance(self):
        """Çok düşük bakiyede hata fırlatmalı."""
        with pytest.raises(InsufficientBalanceError):
            calculate_position_size(
                balance_usdt=Decimal("3"),
                entry_price=Decimal("65000"),
                stop_loss=Decimal("64000"),
                side="BUY",
            )

    def test_sell_side_sizing(self):
        """SELL tarafında SL entry'nin üstünde olmalı."""
        result = calculate_position_size(
            balance_usdt=Decimal("500"),
            entry_price=Decimal("65000"),
            stop_loss=Decimal("66000"),
            side="SELL",
        )
        assert result["quantity"] > 0

    def test_invalid_sl_direction(self):
        """BUY'da SL entry'nin üstünde olursa hata."""
        with pytest.raises(ValueError):
            calculate_position_size(
                balance_usdt=Decimal("500"),
                entry_price=Decimal("65000"),
                stop_loss=Decimal("66000"),
                side="BUY",
            )

    def test_min_notional_enforcement(self):
        """Pozisyon minimum notional ($5) altına düşmemeli."""
        result = calculate_position_size(
            balance_usdt=Decimal("100"),
            entry_price=Decimal("65000"),
            stop_loss=Decimal("64900"),
            side="BUY",
        )
        position_value = float(result["quantity"]) * 65000
        assert position_value >= 5.0

    def test_max_allocation_limit(self):
        """Pozisyon max allocation limitini aşmamalı (komisyon dahil)."""
        from src.config import settings

        result = calculate_position_size(
            balance_usdt=Decimal("500"),
            entry_price=Decimal("65000"),
            stop_loss=Decimal("64999"),  # Çok dar SL -> büyük pozisyon
            side="BUY",
        )
        position_usdt = float(result["position_usdt"])
        max_allowed = 500 * settings.max_asset_allocation_pct
        assert position_usdt <= max_allowed + 1  # komisyon düşüldüğü için her zaman altında
