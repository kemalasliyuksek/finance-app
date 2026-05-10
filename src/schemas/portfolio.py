"""Portföy şemaları."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class PortfolioSnapshotRead(BaseModel):
    id: int
    total_balance_usdt: Decimal
    free_balance_usdt: Decimal
    locked_balance_usdt: Decimal
    unrealized_pnl: Decimal
    open_positions: int
    asset_breakdown: dict
    snapshot_at: datetime

    model_config = {"from_attributes": True}


class PortfolioSummary(BaseModel):
    current_balance: Decimal
    initial_balance: Decimal
    total_pnl: Decimal
    total_pnl_pct: Decimal
    open_positions: int
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: Decimal
    best_trade_pnl: Decimal
    worst_trade_pnl: Decimal
    avg_trade_pnl: Decimal
