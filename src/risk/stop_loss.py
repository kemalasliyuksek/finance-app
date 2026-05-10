"""Stop-loss ve take-profit hesaplama."""

from __future__ import annotations

from decimal import Decimal

from src.constants import Side
from src.core.logging import get_logger

logger = get_logger("stop_loss")


def calculate_atr_stops(
    entry_price: Decimal,
    atr: float,
    side: str,
    sl_multiplier: float = 1.5,
    tp_multiplier: float = 3.0,
    min_sl_pct: float = 0.005,  # Min %0.5
    max_sl_pct: float = 0.05,   # Max %5
) -> dict:
    """ATR bazli stop-loss ve take-profit hesapla.

    Args:
        entry_price: Giris fiyati
        atr: Average True Range degeri
        side: BUY veya SELL
        sl_multiplier: ATR carpani (SL mesafesi)
        tp_multiplier: ATR carpani (TP mesafesi)
        min_sl_pct: Minimum SL mesafesi (%)
        max_sl_pct: Maximum SL mesafesi (%)

    Returns:
        {"stop_loss": Decimal, "take_profit": Decimal, "sl_pct": float, "tp_pct": float}
    """
    atr_decimal = Decimal(str(atr))
    sl_distance = atr_decimal * Decimal(str(sl_multiplier))
    tp_distance = atr_decimal * Decimal(str(tp_multiplier))

    # Min/max SL sinirlamasi
    min_distance = entry_price * Decimal(str(min_sl_pct))
    max_distance = entry_price * Decimal(str(max_sl_pct))
    sl_distance = max(min_distance, min(sl_distance, max_distance))

    # R:R oranini koru
    rr_ratio = tp_multiplier / sl_multiplier
    tp_distance = sl_distance * Decimal(str(rr_ratio))

    if side == Side.BUY:
        stop_loss = entry_price - sl_distance
        take_profit = entry_price + tp_distance
    else:
        stop_loss = entry_price + sl_distance
        take_profit = entry_price - tp_distance

    sl_pct = float(sl_distance / entry_price) * 100
    tp_pct = float(tp_distance / entry_price) * 100

    return {
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "sl_pct": sl_pct,
        "tp_pct": tp_pct,
    }


def calculate_trailing_stop(
    entry_price: Decimal,
    current_price: Decimal,
    side: str,
    trail_pct: float = 0.01,
) -> Decimal:
    """Trailing stop hesapla.

    Args:
        entry_price: Giris fiyati
        current_price: Mevcut fiyat
        side: BUY veya SELL
        trail_pct: Trail yuzde orani

    Returns:
        Trailing stop fiyati
    """
    trail = current_price * Decimal(str(trail_pct))

    if side == Side.BUY:
        return current_price - trail
    else:
        return current_price + trail
