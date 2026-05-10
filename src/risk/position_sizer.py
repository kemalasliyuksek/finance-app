"""Pozisyon boyutlandirma - risk bazli miktar hesaplama."""

from __future__ import annotations

from decimal import Decimal, ROUND_DOWN

from src.config import settings
from src.constants import BINANCE_FEE_RATE, MIN_NOTIONAL_USDT, Side
from src.core.exceptions import InsufficientBalanceError
from src.core.logging import get_logger

logger = get_logger("position_sizer")


def calculate_position_size(
    balance_usdt: Decimal,
    entry_price: Decimal,
    stop_loss: Decimal,
    side: str,
    risk_pct: float | None = None,
    commission_rate: float | None = None,
) -> dict:
    """Risk bazlı pozisyon büyüklüğü hesapla.

    Formül: risk_amount = balance * risk_pct
            position_size = risk_amount / abs(entry - stop_loss)
            quantity = position_size / entry_price

    Komisyon giriş ve çıkışta (2x) hesaplanır ve pozisyon büyüklüğünden
    düşülür, böylece gerçek risk hedefi aşmaz.

    Args:
        balance_usdt: Mevcut USDT bakiye
        entry_price: Giriş fiyatı
        stop_loss: Stop-loss fiyatı
        side: BUY veya SELL
        risk_pct: Trade başına risk oranı (None ise config'den)
        commission_rate: Komisyon oranı (None ise BINANCE_FEE_RATE)

    Returns:
        {
            "quantity": Decimal,           # Coin miktarı
            "position_usdt": Decimal,      # Pozisyon USDT değeri
            "risk_usdt": Decimal,          # Risk miktarı (USDT)
            "risk_pct": float,             # Risk oranı
            "sl_distance_pct": float,      # SL mesafesi (%)
            "commission_estimate": Decimal, # Tahmini komisyon (giriş+çıkış)
        }
    """
    risk = Decimal(str(risk_pct or settings.risk_per_trade_pct))
    fee = Decimal(str(commission_rate or BINANCE_FEE_RATE))

    # Risk miktarı (USDT)
    risk_usdt = balance_usdt * risk

    # SL mesafesi
    if side == Side.BUY:
        sl_distance = entry_price - stop_loss
    else:
        sl_distance = stop_loss - entry_price

    if sl_distance <= 0:
        raise ValueError(f"Geçersiz SL mesafesi: entry={entry_price}, sl={stop_loss}, side={side}")

    sl_distance_pct = float(sl_distance / entry_price) * 100

    # Pozisyon büyüklüğü (brüt)
    position_usdt = risk_usdt / (sl_distance / entry_price)

    # Bakiye kontrolü (önce max allocation limiti)
    max_allocation = balance_usdt * Decimal(str(settings.max_asset_allocation_pct))
    position_usdt = min(position_usdt, max_allocation)

    # Komisyon düşür (giriş + çıkış = 2x komisyon)
    commission_cost = position_usdt * fee * Decimal("2")
    position_usdt = position_usdt - commission_cost

    # Coin miktarı
    quantity = (position_usdt / entry_price).quantize(Decimal("0.00000001"), rounding=ROUND_DOWN)
    position_usdt = quantity * entry_price

    # Minimum notional kontrolü
    if position_usdt < Decimal(str(MIN_NOTIONAL_USDT)):
        if balance_usdt < Decimal(str(MIN_NOTIONAL_USDT)):
            raise InsufficientBalanceError(
                f"Yetersiz bakiye: {balance_usdt} USDT < min notional {MIN_NOTIONAL_USDT}"
            )
        # Minimum notional'a çıkart
        quantity = (Decimal(str(MIN_NOTIONAL_USDT)) / entry_price).quantize(
            Decimal("0.00000001"), rounding=ROUND_DOWN
        )
        position_usdt = quantity * entry_price

    # Gerçek risk miktarı (düzeltilmiş pozisyonla)
    actual_risk_usdt = quantity * sl_distance

    # Tahmini komisyon (giriş + çıkış)
    commission_estimate = position_usdt * fee * Decimal("2")

    logger.info(
        "position_sized",
        balance=float(balance_usdt),
        entry=float(entry_price),
        sl=float(stop_loss),
        quantity=float(quantity),
        position_usdt=float(position_usdt),
        risk_usdt=float(actual_risk_usdt),
        commission_estimate=float(commission_estimate),
        sl_distance_pct=round(sl_distance_pct, 2),
    )

    return {
        "quantity": quantity,
        "position_usdt": position_usdt,
        "risk_usdt": actual_risk_usdt,
        "risk_pct": float(risk),
        "sl_distance_pct": sl_distance_pct,
        "commission_estimate": commission_estimate,
    }
