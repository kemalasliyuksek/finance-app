"""Trade şemaları."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

from src.constants import Side, TradeStatus


class TradeRead(BaseModel):
    id: uuid.UUID
    symbol: str
    side: Side
    entry_price: Decimal
    exit_price: Decimal | None
    quantity: Decimal
    realized_pnl: Decimal | None
    realized_pnl_pct: Decimal | None
    total_commission: Decimal
    status: TradeStatus
    opened_at: datetime
    closed_at: datetime | None
    duration_seconds: int | None

    model_config = {"from_attributes": True}
