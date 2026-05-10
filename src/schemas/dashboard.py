"""Dashboard özet şemaları."""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel

from src.schemas.signal import SignalRead


class DashboardSummary(BaseModel):
    total_balance_usdt: Decimal
    free_balance_usdt: Decimal
    unrealized_pnl: Decimal
    open_positions: int
    today_pnl: Decimal
    today_trades_count: int
    win_rate: Decimal
    recent_signals: list[SignalRead]
    app_mode: str
    trading_mode: str
    active_pairs: list[str]
    is_sandbox: bool = False
