"""Candle (mum) şemaları."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class CandleBase(BaseModel):
    symbol: str
    interval: str
    open_time: datetime
    close_time: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    quote_volume: Decimal
    trade_count: int


class CandleCreate(CandleBase):
    pass


class CandleRead(CandleBase):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}
